import argparse 
import os 
import shutil
import natsort
from tqdm import tqdm 
import tarfile
import regex as re
from fuzzysearch import find_near_matches 
from PIL import Image, ImageDraw
from utils import remove_processed_from_id_list, compress_dir

def find_word_idx_for_span(text, start_idx, end_idx):
    new_splitted_text = (
        text[:start_idx].split() 
        + ["<IS_ABSTRACT>"] * len(text[start_idx: end_idx].split())
        + text[end_idx:].split()
    )

    abstract_idx = [
        i for i, w in enumerate(new_splitted_text) if w == "<IS_ABSTRACT>"
    ]

    return (abstract_idx[0], abstract_idx[-1])

def find_abstract_span(text, abstract_text, max_l_dist=15):
    start_idx = text.find(abstract_text)
    
    if start_idx != -1:
        end_idx = start_idx + len(abstract_text)
        abstract_idx = find_word_idx_for_span(text, start_idx, end_idx)
        return abstract_idx

    matches = find_near_matches(abstract_text, text, max_l_dist=max_l_dist)

    if matches:
        start_idx = matches[0].start
        end_idx = matches[0].end

        abstract_idx = find_word_idx_for_span(text, start_idx, end_idx)
        return abstract_idx

    match = re.search("(?:" + re.escape(abstract_text) + "){e<=5}", text)

    if match:
        span = match.span()
        start_idx = span[0]
        end_idx = span[1] 

        abstract_idx = find_word_idx_for_span(text, start_idx, end_idx)
        return abstract_idx

    return None 


def _update_text(page_path, doc_lines, abstract_span):
    with open(page_path, "w", encoding="utf-8") as f:
        for i, line in enumerate(doc_lines):
            if i < abstract_span[0] or i > abstract_span[1]:
                f.write(line + "\n")

def _update_image(image_path, doc_lines, abstract_span):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size
    width, height = doc_lines[0].split("\t")[5:7]
    width, height = int(width), int(height)
    scale_w = img_width / width
    scale_h = img_height / height

    for i, line in enumerate(doc_lines):
        if i >= abstract_span[0] and i <= abstract_span[1]:
            line = line.split("\t")
            box = line[1:5]
            box = [int(b) for b in box]
            scaled_box = [box[0] * scale_w, box[1] * scale_h, box[2] * scale_w, box[3] * scale_h]

            draw.rectangle(scaled_box, fill="black")

    image.save(image_path)
    image.close()

def update_page(
    page_path, 
    image_path, 
    doc_lines, 
    abstract_span,
):
    _update_text(page_path, doc_lines, abstract_span)
    _update_image(image_path, doc_lines, abstract_span)
    
def extract_from_txt(page_path):
    with open(page_path, "r", encoding="utf-8") as f:
        page_content = f.read().splitlines()

    return page_content

def find_and_remove(args):
    doc_dirs = sorted(os.listdir(args.text_dir))
    doc_dirs = doc_dirs[:args.n_docs] if args.n_docs > 0 else doc_dirs 

    if args.resume_processing:
        ext = ".tar.gz"
        doc_dirs = [doc[:-len(ext)] for doc in doc_dirs]
        print("Resuming processing...")
        doc_dirs = remove_processed_from_id_list(
            doc_dirs, args.found_output_log, args.failed_output_log
        )
        if not doc_dirs:
            print(f"All documents in {args.text_dir} have already been processed.")
            return 
        doc_dirs = [doc + ext for doc in doc_dirs]

    for doc_tar in tqdm(doc_dirs):
        doc_id = doc_tar.replace(".tar.gz", "")
        abstract_path = os.path.join(args.abstract_dir, doc_id + ".txt")
        abstract_text = " ".join(extract_from_txt(abstract_path))

        txt_tar_path = os.path.join(args.text_dir, doc_tar)
        img_tar_path = os.path.join(args.img_dir, doc_tar)

        with tarfile.open(txt_tar_path) as tar:
            tar.extractall(args.output_text_dir) 

        # output folders where text and image are extracted
        doc_txt_folder = os.path.join(args.output_text_dir, doc_id)
        doc_img_folder = os.path.join(args.output_img_dir, doc_id)

        pages = natsort.natsorted(os.listdir(doc_txt_folder))

        abstract_found = False

        for p in pages:
            page_num = p.split("-")[-1].replace(".txt", "")
            page_path = os.path.join(doc_txt_folder, p)

            page_content = extract_from_txt(page_path)
            text = " ".join([line.split("\t")[0] for line in page_content])
            
            abstract_idx = find_abstract_span(
                text, abstract_text, args.max_l_dist
            )
            if not abstract_idx: 
                continue 
            else:
                with tarfile.open(img_tar_path) as tar:
                    tar.extractall(args.output_img_dir) 

                image_page_path = os.path.join(
                    doc_img_folder, 
                    f"{doc_id}-{page_num}.jpg"
                )

                update_page(
                    page_path, 
                    image_page_path, 
                    page_content, 
                    abstract_idx,
                )

                abstract_found = True 
                break

        if abstract_found:
            output_img_tar_path = os.path.join(args.output_img_dir, doc_tar)
            compress_dir(output_img_tar_path, doc_img_folder)
            shutil.rmtree(doc_img_folder)

            with open(args.found_output_log, "a") as f:
                f.write(doc_id + "\n")
        else:
            with open(args.failed_output_log, "a") as f:
                f.write(doc_id + "\n")

        output_txt_tar_path = os.path.join(args.output_text_dir, doc_tar)
        compress_dir(output_txt_tar_path, doc_txt_folder)
        shutil.rmtree(doc_txt_folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--text_dir",
        default=None,
        type=str,
        required=True,
        help="The input data dir. Should contain the txt files.",
    )
    parser.add_argument(
        "--abstract_dir",
        default=None,
        type=str,
        required=True,
    )
    parser.add_argument(
        "--img_dir",
        default=None,
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_text_dir",
        default=None,
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_img_dir",
        default=None,
        type=str,
        required=True,
    )
    # parser.add_argument(
    #     "--dataset_type",
    #     type=str,
    #     required=True,
    #     help="arXiv, PubMed or HAL."
    # )
    parser.add_argument(
        "--n_docs", 
        type=int,
        default=5,
    )
    parser.add_argument(
        "--max_l_dist", 
        type=int,
        default=15,
    )
    parser.add_argument(
        "--found_output_log",
        type=str,
        default="./found_abstract.log"
    )
    parser.add_argument(
        "--failed_output_log",
        type=str,
        default="./no_abstract.log"
    )
    parser.add_argument(
        "--resume_processing", 
        action="store_true", 
        help="Resume processing."
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
    )

    args = parser.parse_args()

    if args.resume_processing and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume_conversion and --overwrite_output_dir at the same time."
        )

    if (
        (os.listdir(args.output_text_dir) or os.listdir(args.output_img_dir)) 
        and not args.resume_processing
    ):
        if args.overwrite_output_dir:
            print(f"Overwriting {args.output_text_dir}")
            shutil.rmtree(args.output_text_dir)
            os.makedirs(args.output_text_dir)

            print(f"Overwriting {args.output_img_dir}")
            shutil.rmtree(args.output_img_dir)
            os.makedirs(args.output_img_dir)

            print(f"Overwriting {args.found_output_log}")
            os.remove(args.found_output_log)

            if os.path.isfile(args.failed_output_log):
                print(f"Overwriting {args.failed_output_log}")
                os.remove(args.failed_output_log)
        else:
            if os.listdir(args.output_text_dir):
                raise ValueError(
                    f"Output directory ({args.output_text_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.listdir(args.output_img_dir):
                raise ValueError(
                    f"Output directory ({args.output_img_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            

    find_and_remove(args)