from sys import prefix
from typing import Optional, Union
import subprocess
from subprocess import PIPE
from pathlib import Path
import os
import shutil
import argparse
from tqdm import tqdm


def pdf2flowhtml(
    input_dir: Union[Path, str],
    pdf_folder: Union[Path, str],
    filepath: Union[Path, str],
    outputfile: Union[Path, str],
    use_docker,
) -> str:

    if use_docker:
        prefix_command = "sudo docker run --rm -v {}:/pdf -v /tmp:/tmp poppler pdftotext -bbox-layout"
    else:
        prefix_command = "pdftotext -bbox-layout"

    command = "{} '{}' '{}'".format(
        prefix_command,
        os.path.abspath(input_dir),
        os.path.join(pdf_folder, filepath),
        os.path.join("html", outputfile)
    )
    subprocess.call(command, shell=True)


def convert(args):
    fnames = sorted(
        os.listdir(
            os.path.join(args.input_dir, args.pdf_folder)
        )
    )

    for filename in tqdm(fnames, desc=f"Processing PDFs in {args.input_dir}"):
        output_fname = filename[:-4] + ".html"
        pdf2flowhtml(args.input_dir, args.pdf_folder, filename, output_fname, args.use_docker)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir", 
        type=str,
        required=True,
        help="The input directory. Should be one folder above the one containing the PDF files."
    )
    parser.add_argument(
        "--pdf_folder", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_folder", 
        type=str,
        default="html"
    )
    parser.add_argument(
        "--use_docker", 
        action="store_true", 
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    output_dir = os.path.join(args.input_dir, args.output_folder)
    if os.listdir(output_dir):
        if args.overwrite_output_dir:
            print(f"Overwriting {output_dir}")
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
        else:
            raise ValueError(
                f"Output directory ({output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )


    convert(args)