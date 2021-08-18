import argparse 
import os
import shutil
from tqdm import tqdm 
import tarfile
from pdf2image import convert_from_path

def remove_converted(fname_list, converted_log):
    """ Removes from list documents that have already been converted 

    Args:
        fname_list (list): list of PDF names 
        converted_log (string): path to log containing IDs of converted documents
    Returns:
        list: list of document IDs whose PDF has not been converted yet
    """
    if os.path.isfile(converted_log):
        with open(args.converted_output_log, "r") as f:
            converted = f.read().splitlines()
    else:
        converted = []

    fname_list = [doc_id for doc_id in fname_list if doc_id not in converted] 
    return fname_list

def convert(args):
    fnames = sorted(os.listdir(args.input_dir))
    fnames = remove_converted(fnames, args.converted_output_log)
    if args.n_docs > 0:
        fnames = fnames[:args.n_docs]

    for fname in tqdm(fnames):
        pdf_path = os.path.join(args.input_dir, fname)
        output_folder = os.path.join(args.output_dir, fname[:-4])

        # convert
        os.makedirs(output_folder)
        convert_from_path(
            pdf_path, 
            dpi=300, 
            fmt="jpg",
            first_page=args.first_page,
            output_file=fname[:-4],
            output_folder=output_folder,
        )

        # compress output images
        tar_path = os.path.join(args.output_dir, fname[:-4] + ".tar.gz")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(output_folder, arcname=os.path.basename(output_folder)) 

        shutil.rmtree(output_folder)

        with open(args.converted_output_log, "a") as f:
            f.write(fname[:-4] + "\n")
       


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

    if args.resume_download and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume_download and --overwrite_output_dir at the same time."
        )

    if os.listdir(args.output_dir) and not args.resume_download:
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