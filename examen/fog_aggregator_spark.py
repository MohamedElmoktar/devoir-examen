"""
Fog Aggregator: Agrégation régionale avec Spark Structured Streaming
Agrège les updates de modèles par région avant envoi au Cloud
"""

import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, avg, sum as spark_sum,
    collect_list, current_timestamp, expr
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, MapType, ArrayType
)
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FogAggregator:
    """Agrégateur Fog utilisant Spark Structured Streaming"""

    def __init__(self):
        self.spark = None

    def create_spark_session(self):
        """Crée la session Spark avec config Kafka"""
        self.spark = SparkSession.builder \
            .appName("FogAggregator") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint") \
            .config("spark.sql.shuffle.partitions", "4") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("✓ Spark Session créée")

    def define_schema(self):
        """Définit le schéma des messages edge_weights"""
        metrics_schema = StructType([
            StructField("local_accuracy", DoubleType(), True),
            StructField("total_samples", IntegerType(), True),
            StructField("anomalies_detected", IntegerType(), True)
        ])

        weights_schema = StructType([
            StructField("coef", ArrayType(ArrayType(DoubleType())), True),
            StructField("intercept", ArrayType(DoubleType()), True),
            StructField("classes", ArrayType(IntegerType()), True)
        ])

        schema = StructType([
            StructField("edge_id", StringType(), False),
            StructField("region", StringType(), False),
            StructField("round", IntegerType(), False),
            StructField("timestamp", StringType(), False),
            StructField("n_samples", IntegerType(), False),
            StructField("weights", weights_schema, False),
            StructField("metrics", metrics_schema, True)
        ])

        return schema

    def aggregate_by_region(self, edge_weights_df):
        """Agrège les poids par région et fenêtre temporelle"""

        # Agrégation par région sur fenêtre glissante
        aggregated = edge_weights_df \
            .withWatermark("event_time", config.FOG_WATERMARK_DELAY) \
            .groupBy(
                window(col("event_time"), config.FOG_WINDOW_DURATION),
                col("region")
            ) \
            .agg(
                collect_list("edge_id").alias("contributing_edges"),
                collect_list("weights").alias("all_weights"),
                spark_sum("n_samples").alias("total_n_samples"),
                avg("metrics.local_accuracy").alias("avg_accuracy"),
                spark_sum("metrics.anomalies_detected").alias("total_anomalies")
            ) \
            .select(
                col("region"),
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("contributing_edges"),
                col("all_weights"),
                col("total_n_samples"),
                col("avg_accuracy"),
                col("total_anomalies"),
                current_timestamp().alias("fog_timestamp")
            )

        return aggregated

    def run(self):
        """Lance le streaming Spark"""
        logger.info("🚀 Démarrage Fog Aggregator (Spark Structured Streaming)")

        schema = self.define_schema()

        # Lecture depuis Kafka
        kafka_df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS[0]) \
            .option("subscribe", config.KAFKA_TOPICS['edge_weights']) \
            .option("startingOffsets", "latest") \
            .load()

        # Parse JSON
        edge_weights_df = kafka_df \
            .selectExpr("CAST(value AS STRING) as json_value", "timestamp as kafka_timestamp") \
            .select(from_json(col("json_value"), schema).alias("data"), col("kafka_timestamp")) \
            .select("data.*", col("kafka_timestamp").alias("event_time"))

        # Agrégation
        aggregated_df = self.aggregate_by_region(edge_weights_df)

        # Conversion pour Kafka (format JSON string)
        output_df = aggregated_df.selectExpr(
            "region as key",
            "to_json(struct(*)) AS value"
        )

        # Écriture vers Kafka
        query = output_df \
            .writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS[0]) \
            .option("topic", config.KAFKA_TOPICS['fog_agg']) \
            .option("checkpointLocation", "/tmp/spark-checkpoint-fog") \
            .outputMode("update") \
            .start()

        # Console output pour monitoring
        console_query = aggregated_df \
            .writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .start()

        logger.info("✓ Fog Aggregator en écoute sur edge_weights...")
        logger.info(f"  Fenêtre: {config.FOG_WINDOW_DURATION}")
        logger.info(f"  Watermark: {config.FOG_WATERMARK_DELAY}")

        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("\n⏹  Arrêt Fog Aggregator")
            query.stop()
            console_query.stop()
            self.spark.stop()


def main():
    aggregator = FogAggregator()
    aggregator.create_spark_session()
    aggregator.run()


if __name__ == '__main__':
    main()
