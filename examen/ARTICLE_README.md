# Scientific Article - LaTeX Compilation Guide

This directory contains a scientific article about the Federated Learning Edge-Fog-Cloud architecture.

## 📄 Files

- `article.tex` - Main LaTeX source file
- `Makefile` - Build automation for local compilation
- `ARTICLE_README.md` - This file

## 📊 Article Contents

The article covers:
- Abstract and Introduction
- System Architecture (Edge-Fog-Cloud)
- Federated Learning Algorithm (FedAvg)
- Implementation details
- Experimental Results
- Discussion and Future Work
- References

## 🚀 Option 1: Compile Locally (Recommended if you have LaTeX)

### Install LaTeX on macOS

```bash
# Install MacTeX (full distribution, ~4GB)
brew install --cask mactex

# OR install BasicTeX (minimal, ~100MB)
brew install --cask basictex
```

After installation, restart your terminal or run:
```bash
eval "$(/usr/libexec/path_helper)"
```

### Compile the PDF

```bash
# Simple compilation
pdflatex article.tex
pdflatex article.tex  # Run twice for references

# Or use the Makefile
make all

# View the PDF
make view

# Clean auxiliary files
make clean
```

## 🌐 Option 2: Use Overleaf (Online - No Installation Required)

**Overleaf** is a free online LaTeX editor. This is the easiest option if you don't want to install LaTeX locally.

### Steps:

1. Go to [https://www.overleaf.com](https://www.overleaf.com)
2. Create a free account (if you don't have one)
3. Click "New Project" → "Blank Project"
4. Name your project: "Federated Learning Article"
5. Delete the default `main.tex` file
6. Click "Upload" and upload `article.tex`
7. Click on `article.tex` in the file list
8. The PDF will automatically compile and appear on the right side
9. Download the PDF using the "Download PDF" button

### Advantages of Overleaf:
- ✅ No installation needed
- ✅ Automatic compilation
- ✅ Preview in real-time
- ✅ Cloud-based (access anywhere)
- ✅ Collaboration features
- ✅ Version control built-in

## 🌐 Option 3: Use Other Online LaTeX Editors

### CoCalc (formerly SageMathCloud)
- URL: [https://cocalc.com](https://cocalc.com)
- Free tier available
- Similar to Overleaf

### Papeeria
- URL: [https://papeeria.com](https://papeeria.com)
- Free plan available

## 📝 Editing the Article

To modify the article:

1. Open `article.tex` in any text editor
2. Edit the content between `\begin{document}` and `\end{document}`
3. Recompile to see changes

### Key Sections to Edit:

```latex
% Author information (line 12)
\IEEEauthorblockN{Mohamed Elmokhtar Hadoueni}

% Abstract (line 21)
\begin{abstract}
...
\end{abstract}

% Main content (sections)
\section{Introduction}
...
```

## 🔧 Troubleshooting Local Compilation

### Missing packages error

If you get "File XXX.sty not found":

```bash
# For MacTeX/BasicTeX
sudo tlmgr update --self
sudo tlmgr install <package-name>

# Common packages for this article
sudo tlmgr install IEEEtran
sudo tlmgr install cite
sudo tlmgr install hyperref
```

### Path issues after installing MacTeX

```bash
# Add to your ~/.zshrc or ~/.bash_profile
export PATH="/Library/TeX/texbin:$PATH"

# Then reload
source ~/.zshrc  # or source ~/.bash_profile
```

## 📖 LaTeX Resources

### Learn LaTeX
- [Overleaf LaTeX Tutorial](https://www.overleaf.com/learn)
- [LaTeX Wikibook](https://en.wikibooks.org/wiki/LaTeX)
- [IEEE Template Documentation](https://www.ieee.org/conferences/publishing/templates.html)

### IEEE Conference Template
This article uses the IEEE conference template (`IEEEtran.cls`). This is standard for:
- IEEE conferences
- Computer science publications
- Engineering papers

## 📊 Article Statistics

- **Format:** IEEE Conference Paper
- **Length:** ~6 pages (standard for conference papers)
- **Sections:** 8 main sections + references
- **Tables:** 2
- **References:** 6 citations

## 🎯 Next Steps

After compiling:

1. **Review the PDF** - Check formatting, figures, tables
2. **Add figures** - Consider adding architecture diagrams
3. **Expand results** - Add more experimental data if available
4. **Proofread** - Check grammar and technical accuracy
5. **Get feedback** - Share with peers or advisor

## 📄 Export Options

Once compiled, you can:
- **Print** - Use the generated PDF
- **Submit** - Upload to conference systems
- **Share** - Email or upload to repository
- **Archive** - Include in your project documentation

## 🤝 Contributing

To improve this article:
1. Edit `article.tex`
2. Compile and verify changes
3. Commit to git repository

## 📞 Support

If you encounter issues:
- Check LaTeX logs (`.log` file)
- Search error messages on [TeX StackExchange](https://tex.stackexchange.com)
- Use Overleaf's built-in help resources

---

**Happy Writing! 🎓**
