from sys import prefix
from typing import Optional, Union
import subprocess
from subprocess import PIPE
from pathlib import Path
import os
import shutil
import argparse
from tqdm import tqdm
from utils import remove_converted_from_id_list

def pdf2flowhtml(
    input_dir: Union[Path, str],
    pdf_folder: Union[Path, str],
    filepath: Union[Path, str],
    output_folder: Union[Path, str],
    outputfile: Union[Path, str],
    use_docker,
) -> str:

    if use_docker:
        command = "sudo docker run --rm -v {}:/pdf -v /tmp:/tmp poppler pdftotext -bbox-layout '{}' '{}'".format(
            os.path.abspath(input_dir),
            os.path.join(pdf_folder, filepath),
            os.path.join(output_folder, outputfile)
        )
    else:
        command = "pdftotext -bbox-layout '{}' '{}'".format(
            os.path.join(
                os.path.join(input_dir, pdf_folder),
                filepath
            ),
            os.path.join(
                os.path.join(input_dir, output_folder),
                filepath
            ),
        )
    
    subprocess.call(command, shell=True)


def convert(args):
    fnames = sorted(os.listdir(
        os.path.join(args.input_dir, args.pdf_folder)
    ))
    fnames = fnames[:args.n_docs] if args.n_docs > 0 else fnames 

    if args.resume_conversion:
        fnames = remove_converted_from_id_list(fnames, args.converted_output_log)
        if not fnames:
            print(f"All documents in {args.input_file} have already been converted to HTML")
            return

    for filename in tqdm(fnames, desc=f"Processing PDFs in {args.input_dir}"):
        output_fname = filename[:-4] + ".html"
        pdf2flowhtml(args.input_dir, args.pdf_folder, filename, args.output_folder, output_fname, args.use_docker)


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
        "--n_docs", 
        type=int,
        default=5,
    )
    parser.add_argument(
        "--converted_output_log",
        type=str,
        default="./converted_to_img.log"
    )
    parser.add_argument(
        "--resume_conversion", 
        action="store_true", 
        help="Resume download."
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if args.resume_conversion and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume_conversion and --overwrite_output_dir at the same time."
        )

    output_dir = os.path.join(args.input_dir, args.output_folder)
    if os.listdir(output_dir) and not args.resume_conversion:
        if args.overwrite_output_dir:
            print(f"Overwriting {output_dir}")
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)

            print(f"Overwriting {args.converted_output_log}")
            os.remove(args.converted_output_log)
        else:
            raise ValueError(
                f"Output directory ({output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )


    convert(args)