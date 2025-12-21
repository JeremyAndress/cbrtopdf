import subprocess
import sys
import shutil
import pikepdf
from pathlib import Path
from PIL import Image
import typer
from cbrtopdf.logger import logger
from cbrtopdf.constants import IMAGE_EXTENSIONS, ReadingDirecctionEnum

app = typer.Typer(help="Convert CBR files to PDF")


def extract_cbr(cbr_path: Path, output_dir: Path):
    logger.info(f"Extracting archive: {cbr_path.name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["unrar", "x", "-o+", str(cbr_path), f"{output_dir}/"], check=True)


def collect_images(
    root_dir: Path,
    split_horizontal=False,
    rotate_if_horizontal=False,
    reading_direction=ReadingDirecctionEnum.LEFT_TO_RIGHT.value,
):
    images = []
    chapters = []
    current_dir = root_dir
    temp_dir = root_dir / "__processed__"

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

    direct_images = sorted(
        [
            f
            for f in current_dir.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda p: p.name,
    )

    if direct_images:
        logger.info(f"Processing images in: {current_dir}")

        for img in direct_images:
            if split_horizontal:
                images.extend(split_if_horizontal(img, temp_dir, reading_direction))
            elif rotate_if_horizontal:
                images.append(rotate_if_horizontal(img, temp_dir))
            else:
                images.append(img)

        return images, []

    folders = sorted(
        [d for d in current_dir.iterdir() if d.is_dir()], key=lambda p: p.name
    )

    page_index = 0

    for folder in folders:
        logger.info(f"Processing chapter: {folder.name}")

        chapter_images = sorted(
            [
                f
                for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            ],
            key=lambda p: p.name,
        )

        if not chapter_images:
            continue

        chapters.append((folder.name, page_index))

        for img in chapter_images:
            if split_horizontal:
                split_pages = split_if_horizontal(img, temp_dir)
                images.extend(split_pages)
                page_index += len(split_pages)
            elif rotate_if_horizontal:
                images.append(rotate_if_horizontal(img, temp_dir))
                page_index += 1
            else:
                images.append(img)
                page_index += 1

    if not images:
        raise RuntimeError("No images were found")

    logger.info(f"Total final pages: {len(images)}")
    logger.info(f"Detected chapters: {len(chapters)}")
    return images, chapters


def split_if_horizontal(
    img_path: Path,
    temp_dir: Path,
    reading_direction=ReadingDirecctionEnum.LEFT_TO_RIGHT.value,
):
    with Image.open(img_path) as img:
        width, height = img.size

        if width <= height:
            return [img_path]

        logger.info(f"Splitting horizontal page: {img_path.name}")

        half = width // 2

        left = img.crop((0, 0, half, height))
        right = img.crop((half, 0, width, height))

        temp_dir.mkdir(parents=True, exist_ok=True)

        left_path = temp_dir / f"{img_path.stem}_left.{img.format}"
        right_path = temp_dir / f"{img_path.stem}_right.{img.format}"

        left.save(left_path, f"{img.format.upper()}", quality=98)
        right.save(right_path, f"{img.format.upper()}", quality=98)

        return (
            [left_path, right_path]
            if reading_direction == ReadingDirecctionEnum.LEFT_TO_RIGHT.value
            else [right_path, left_path]
        )


def rotate_if_horizontal(img_path: Path, temp_dir: Path):
    with Image.open(img_path) as img:
        width, height = img.size

        if width <= height:
            return img_path
        logger.info(f"Rotating horizontal image to vertical: {img_path.name}")
        rotated = img.rotate(-90, expand=True)

        temp_dir.mkdir(parents=True, exist_ok=True)

        rotated_path = temp_dir / f"{img_path.stem}_rotated.{img.format}"
        rotated.save(rotated_path, f"{img.format.upper()}", quality=98)

        return rotated_path


def add_pdf_bookmarks(pdf_path: Path, chapters):
    if not chapters:
        logger.info("No chapters detected, skipping PDF bookmarks")
        return

    logger.info("Adding PDF bookmarks")

    pdf = pikepdf.open(pdf_path, allow_overwriting_input=True)

    with pdf.open_outline() as outline:
        for title, page in chapters:
            outline.root.append(pikepdf.OutlineItem(f"Chapter {title}", page))

    pdf.save(pdf_path)


def build_pdf(images, output_pdf: Path):
    logger.info(f"Generating PDF: {output_pdf.name}")
    cmd = ["img2pdf", *map(str, images), "-o", str(output_pdf)]
    subprocess.run(cmd, check=True)


def cleanup(output_dir: Path):
    logger.info(f"Removing temporary directory: {output_dir}")
    shutil.rmtree(output_dir)


@app.command()
def convert(
    file: Path = typer.Argument(..., exists=True, help="Input .cbr file"),
    keep_extracted: bool = typer.Option(
        False, "--keep-extracted", help="Keep extracted files"
    ),
    split_horizontal: bool = typer.Option(
        False, "--split-horizontal", help="Split horizontal pages"
    ),
    rotate_if_horizontal: bool = typer.Option(
        False, "--rotate-if-horizontal", help="Rotate horizontal pages"
    ),
    reading_direction: str = typer.Option(
        "ltr",
        "--reading-direction",
        help="Reading direction for split pages",
        case_sensitive=False,
    ),
):
    if split_horizontal and rotate_if_horizontal:
        typer.echo(
            "Error: --split-horizontal and --rotate-if-horizontal cannot be used together",
            err=True,
        )
        raise typer.Exit(code=1)

    if reading_direction not in {"ltr", "rtl"}:
        typer.echo("Error: --reading-direction must be 'ltr' or 'rtl'", err=True)
        raise typer.Exit(code=1)

    if reading_direction == "rtl" and not split_horizontal:
        typer.echo(
            "Warning: --reading-direction has no effect without --split-horizontal"
        )
    output_dir = file.with_suffix("")
    output_pdf = file.with_suffix(".pdf")

    try:
        extract_cbr(file, output_dir)
        images, chapters = collect_images(
            output_dir, split_horizontal, rotate_if_horizontal, reading_direction
        )
        build_pdf(images, output_pdf)
        add_pdf_bookmarks(output_pdf, chapters)

        if not keep_extracted:
            cleanup(output_dir)
        else:
            logger.info("Keeping extracted files (--keep-extracted)")

        logger.info("Process completed successfully ✅")

    except subprocess.CalledProcessError as e:
        logger.error(f"External command execution failed: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
