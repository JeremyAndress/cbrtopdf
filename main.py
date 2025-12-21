#!/usr/bin/env python3

import subprocess
import sys
import logging
import shutil
import pikepdf
from pathlib import Path
from PIL import Image


# -------------------------
# Logging (solo consola)
# -------------------------
logger = logging.getLogger("cbr2pdf")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}


def extract_cbr(cbr_path: Path, output_dir: Path):
    logger.info(f"Extrayendo: {cbr_path.name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["unrar", "x", "-o+", str(cbr_path), f"{output_dir}/"],
        check=True
    )


def collect_images(root_dir: Path, split_horizontal=False):
    images = []
    chapters = []
    current_dir = root_dir
    temp_split_dir = root_dir / "__split__"

    # 🔽 Auto-descenso de carpetas wrapper
    while True:
        subdirs = [d for d in current_dir.iterdir() if d.is_dir()]
        files = [f for f in current_dir.iterdir() if f.is_file()]

        has_images = any(f.suffix.lower() in IMAGE_EXTENSIONS for f in files)

        if has_images:
            break

        if len(subdirs) == 1:
            current_dir = subdirs[0]
        else:
            break

    # 🔍 Caso 1: imágenes directas → SIN capítulos
    direct_images = sorted(
        [f for f in current_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda p: p.name
    )

    if direct_images:
        logger.info(f"Procesando imágenes en: {current_dir}")

        for img in direct_images:
            if split_horizontal:
                images.extend(split_if_horizontal(img, temp_split_dir))
            else:
                images.append(img)

        return images, []

    # 🔍 Caso 2: carpetas = capítulos
    folders = sorted(
        [d for d in current_dir.iterdir() if d.is_dir()],
        key=lambda p: p.name
    )

    page_index = 0

    for folder in folders:
        logger.info(f"Procesando capítulo: {folder.name}")

        chapter_images = sorted(
            [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
            key=lambda p: p.name
        )

        if not chapter_images:
            continue

        chapters.append((folder.name, page_index))

        for img in chapter_images:
            if split_horizontal:
                split_pages = split_if_horizontal(img, temp_split_dir)
                images.extend(split_pages)
                page_index += len(split_pages)
            else:
                images.append(img)
                page_index += 1

    if not images:
        raise RuntimeError("No se encontraron imágenes")

    logger.info(f"Total de páginas finales: {len(images)}")
    logger.info(f"Capítulos detectados: {len(chapters)}")
    return images, chapters


def split_if_horizontal(img_path: Path, temp_dir: Path):
    with Image.open(img_path) as img:
        width, height = img.size

        if width <= height:
            return [img_path]

        logger.info(f"Cortando página horizontal: {img_path.name}")

        half = width // 2

        left = img.crop((0, 0, half, height))
        right = img.crop((half, 0, width, height))

        temp_dir.mkdir(parents=True, exist_ok=True)

        left_path = temp_dir / f"{img_path.stem}_left.jpg"
        right_path = temp_dir / f"{img_path.stem}_right.jpg"

        left.save(left_path, "JPEG", quality=98)
        right.save(right_path, "JPEG", quality=98)

        return [left_path, right_path]


def add_pdf_bookmarks(pdf_path: Path, chapters):
    if not chapters:
        logger.info("No se detectaron capítulos, se omiten bookmarks")
        return

    logger.info("Agregando bookmarks al PDF")

    pdf = pikepdf.open(pdf_path, allow_overwriting_input=True)

    with pdf.open_outline() as outline:
        for title, page in chapters:
            outline.root.append(
                pikepdf.OutlineItem(f"Capítulo {title}", page)
            )

    pdf.save(pdf_path)


def build_pdf(images, output_pdf: Path):
    logger.info(f"Generando PDF: {output_pdf.name}")
    cmd = ["img2pdf", *map(str, images), "-o", str(output_pdf)]
    subprocess.run(cmd, check=True)


def cleanup(output_dir: Path):
    logger.info(f"Eliminando carpeta temporal: {output_dir}")
    shutil.rmtree(output_dir)


def main():
    if len(sys.argv) < 2:
        logger.error("Uso: python cbr_to_pdf.py archivo.cbr [--keep-extracted]")
        sys.exit(1)

    keep_extracted = "--keep-extracted" in sys.argv
    split_horizontal = "--split-horizontal" in sys.argv
    archive_arg = next(arg for arg in sys.argv[1:] if not arg.startswith("--"))

    cbr_path = Path(archive_arg).resolve()

    if not cbr_path.exists():
        logger.error("Archivo no encontrado")
        sys.exit(1)

    output_dir = cbr_path.with_suffix("")
    output_pdf = cbr_path.with_suffix(".pdf")

    try:
        extract_cbr(cbr_path, output_dir)
        images, chapters = collect_images(output_dir, split_horizontal)
        build_pdf(images, output_pdf)
        add_pdf_bookmarks(output_pdf, chapters)

        if not keep_extracted:
            cleanup(output_dir)
        else:
            logger.info("Manteniendo carpeta extraída (--keep-extracted)")

        logger.info("Proceso completado correctamente ✅")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error ejecutando comando externo: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
