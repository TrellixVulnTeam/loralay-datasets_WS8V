import argparse 
import os
import shutil
import glob
from tqdm import tqdm 
from pdf2image import convert_from_path


def convert(args):
    fnames = os.listdir(args.input_dir)

    for fname in tqdm(fnames):
        pdf_path = os.path.join(args.input_dir, fname)
        output_folder = os.path.join(args.output_dir, fname[:-4])
        os.makedirs(output_folder)
        pages = convert_from_path(
            pdf_path, 
            dpi=300, 
            output_folder=output_folder,
        )
        for i, page in enumerate(pages):
            page.save(
                os.path.join(output_folder, f"{fname[:-4]}_{i+1}.jpg"),
                "JPEG"
            )
        ppm_files = glob.glob(f"{output_folder}/*.ppm")
        for f in ppm_files:
            os.remove(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir", 
        type=str,
    )
    parser.add_argument(
        "--output_dir", 
        type=str,
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if os.listdir(args.output_dir):
        if args.overwrite_output_dir:
            print(f"Overwriting {args.output_dir}")
            shutil.rmtree(args.output_dir)
            os.makedirs(args.output_dir)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )


    convert(args)