import argparse 
import os
import shutil
import glob
from tqdm import tqdm 
import tarfile
from pdf2image import convert_from_path


def convert(args):
    fnames = os.listdir(args.input_dir)

    for fname in tqdm(fnames):
        pdf_path = os.path.join(args.input_dir, fname)
        output_folder = os.path.join(args.output_dir, fname[:-4])
        os.makedirs(output_folder)
        convert_from_path(
            pdf_path, 
            dpi=300, 
            fmt="jpg",
            first_page=args.first_page,
            output_file=fname[:-4],
            output_folder=output_folder,
        )

        tar_path = os.path.join(args.output_dir, fname[:-4] + ".tar.gz")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(output_folder, arcname=os.path.basename(output_folder)) 

        shutil.rmtree(output_folder)
        # for i, page in enumerate(pages):
        #     page.save(
        #         os.path.join(output_folder, f"{fname[:-4]}_{i+1}.jpg"),
        #         "JPEG"
        #     )

        # ppm_files = glob.glob(f"{output_folder}/*.ppm")
        # for f in ppm_files:
        #     os.remove(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--first_page", 
        type=int,
        default=1,
    )
    parser.add_argument(
        "--converted_output_log",
        type=str,
        default="./converted_to_img.log"
    )
    parser.add_argument(
        "--resume_download", 
        action="store_true", 
        help="Resume download."
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

            print(f"Overwriting {args.output_dir}")
            shutil.rmtree(args.output_dir)
            os.makedirs(args.output_dir)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )


    convert(args)