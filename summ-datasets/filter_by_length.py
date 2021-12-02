import argparse 
import os 
from tqdm import tqdm
import shutil

def filter_out(args):
    input_filenames = os.listdir(args.input_dir)

    for filename in tqdm(input_filenames):
        input_path = os.path.join(args.input_dir, filename)
        output_path = os.path.join(args.output_dir, filename)
        with open(input_path, 'r') as input_file:
            doc_length = sum(1 for line in input_file)
            if doc_length >= args.lower_bound:
                if args.upper_bound < 0 or doc_length <= args.upper_bound:
                    shutil.copy(input_path, output_path)


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
        "--lower_bound",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--upper_bound",
        type=int,
        default=-1,
    )

    args = parser.parse_args()

    filter_out(args)