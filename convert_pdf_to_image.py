import argparse 
import os
import shutil
from tqdm import tqdm 
import tarfile
from pdf2image import convert_from_path
from utils import remove_processed_from_id_list, compress_dir

def convert(args):
    fnames = sorted(os.listdir(args.input_dir))
    fnames = fnames[:args.n_docs] if args.n_docs > 0 else fnames 

    if args.resume_conversion:
        print("Resuming conversion...")
        fnames = remove_processed_from_id_list(fnames, args.converted_output_log)
        if not fnames:
            print(f"All documents in {args.input_dir} have already been converted to image")
            return

    for fname in tqdm(fnames):
        doc_id = fname[:-4]
        pdf_path = os.path.join(args.input_dir, fname)
        output_folder = os.path.join(args.output_dir, doc_id)

        # convert
        os.makedirs(output_folder)
        # pages = convert_from_path(
        #     pdf_path, 
        #     dpi=300, 
        #     fmt="jpg",          
        #     first_page=args.first_page,
        #     output_file=fname[:-4],
        #     output_folder=output_folder,
        # )
        pages = convert_from_path(pdf_path, dpi=300)
        for i, p in enumerate(pages):
            p.save(os.path.join(output_folder, doc_id + "-" + str(i+1) + ".jpg"))

        # compress output images
        tar_path = os.path.join(args.output_dir, doc_id + ".tar.gz")
        compress_dir(tar_path, output_folder)
        shutil.rmtree(output_folder)

        with open(args.converted_output_log, "a") as f:
            f.write(doc_id + "\n")
       


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
        "--resume_conversion", 
        action="store_true", 
        help="Resume conversion."
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

    if os.listdir(args.output_dir) and not args.resume_conversion:
        if args.overwrite_output_dir:
            print(f"Overwriting {args.output_dir}")
            shutil.rmtree(args.output_dir)
            os.makedirs(args.output_dir)

            print(f"Overwriting {args.converted_output_log}")
            os.remove(args.converted_output_log)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )


    convert(args)