# 📚 cbrtopdf

cbrtopdf is a command-line tool that converts CBR (Comic Book RAR) files into PDF, with proper support for:

- Comics (left-to-right reading)

- Manga (right-to-left reading)

- Double-page spreads

- Automatic page rotation

- Chapter detection and PDF bookmarks

Built with a focus on correct reading order and clean output, without overcomplicated presets.

## ✨ Features

- 📦 Extracts .cbr archives

- 🖼️ Supports common image formats (JPG, PNG, WEBP, etc.)

- ✂️ Split horizontal double pages into two vertical pages

- 📖 Manga (RTL) and Comic (LTR) reading order

- 🔄 Rotate horizontal pages instead of splitting

- 📑 Automatically adds PDF bookmarks when chapters are detected

- 🧹 Optional cleanup of extracted files

- 🧠 Clear logs and predictable behavior

## 📦 Installation

```
pip install cbrtopdf
```

## 🔧 System Requirements

The following external tools must be installed on your system:

- **unrar**

- **img2pdf**

### Debian / Ubuntu

```
sudo apt install unrar img2pdf
```

## 🚀 Usage
### Basic conversion

```
cbrtopdf convert comic.cbr
```

This will generate:

```
comic.pdf
```
