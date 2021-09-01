import os
import shutil
import argparse
from tqdm import tqdm
from lxml.etree import iterparse
import re
import tarfile
import logging
from utils import remove_processed_from_id_list, compress_dir

logger = logging.getLogger(__name__)


def remove_special_chars(text):
    return re.sub('[^a-zA-Z0-9*\s]', '', text)

def clean_text(text):
    text = re.sub(r"\s+", "", text)
    return text

def extract_text_from_tree(file_path):
    doc = []

    cur_page = []
    page_width = None
    page_height = None

    with open(file_path, 'rb') as f:
        for _, element in iterparse(f, events=("start", "end"), recover=True):
            if "word" in element.tag and element.text:
                word = clean_text(element.text) if element.text else None
                if word:
                    if element.attrib:
                        if page_width == 0 or page_height == 0:
                            continue
                        xmin = round(float(element.attrib['xMin']))
                        xmax = round(float(element.attrib['xMax']))
                        ymin = round(float(element.attrib['yMin']))
                        ymax = round(float(element.attrib['yMax']))

                        xmin, ymin = max(0, xmin), max(0, ymin) # set to 0 if < 0 
                        xmax, ymax = min(page_width, xmax), min(page_height, ymax) # set to max if > max

                        xmin = min(xmin, page_width) # set to max if > max 
                        ymin = min(ymin, page_height) 
                        xmax = max(0, xmax) # set to 0 if < 0
                        ymax = max(0, ymax)

                        if xmin > xmax: # swap if xmin > xmax
                            xmin, xmax = xmax, xmin
                        if ymin > ymax:
                            ymin, ymax = ymax, ymin

                        bbox = tuple([xmin, ymin, xmax, ymax])
                        cur_page.append((word,) + bbox + (page_width, page_height))
            elif "page" in element.tag and element.attrib:
                if len(cur_page) > 0:
                    doc.append(cur_page)
                    cur_page = []
                page_width = round(float(element.attrib["width"]))
                page_height = round(float(element.attrib["height"]))

            element.clear()

    if len(cur_page) > 0:
        doc.append(cur_page)
        cur_page = []

    return doc

def parse(args):
    fnames = sorted(os.listdir(args.html_dir))
    fnames = fnames[:args.n_docs] if args.n_docs > 0 else fnames 

    if args.resume:
        print("Resuming parsing...")
        fnames = remove_processed_from_id_list(
            fnames, args.parsed_output_log, args.failed_output_log
        )
        if not fnames:
            print(f"All documents in {args.input_file} have already been parsed")
            return

    for html in tqdm(fnames):
        html_path = os.path.join(args.html_dir, html)
        doc = extract_text_from_tree(html_path)

        doc_id = html[:-5]
        doc_output_dir = os.path.join(args.output_dir, doc_id)
        os.makedirs(doc_output_dir)

        for i, p in enumerate(doc):
            output_file = os.path.join(
                os.path.join(doc_output_dir, doc_id + "-" + str(i+1) + ".txt")
            )
            with open(output_file, "w", encoding="utf-8") as fw:
                for elem in p:
                    word = elem[0]
                    bbox = elem[1:5]
                    page_width, page_height = elem[5:]

                    bbox_str = (
                        str(bbox[0]) 
                        + "\t" 
                        + str(bbox[1]) 
                        + "\t" 
                        + str(bbox[2]) 
                        + "\t" 
                        + str(bbox[3])
                    )

                    fw.write(
                        word 
                        + "\t" 
                        + bbox_str 
                        + "\t" 
                        + str(page_width) 
                        + "\t" 
                        + str(page_height) 
                        + "\n" 
                    )
        # compress output txt files 
        tar_path = doc_output_dir + ".tar.gz"
        compress_dir(tar_path, doc_output_dir)
        
        shutil.rmtree(doc_output_dir)

        with open(args.parsed_output_log, "a") as f:
            f.write(doc_id + "\n")
                    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--html_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--n_docs", 
        type=int,
        default=5,
    )
    parser.add_argument(
        "--parsed_output_log",
        type=str,
        default="./parsed.log"
    )
    parser.add_argument(
        "--resume", 
        action="store_true", 
        help="Resume download."
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if args.resume and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume and --overwrite_output_dir at the same time."
        )

    if os.listdir(args.output_dir) and not args.resume:
        if args.overwrite_output_dir:
            print(f"Overwriting {args.output_dir}")
            shutil.rmtree(args.output_dir)
            os.makedirs(args.output_dir)

            print(f"Overwriting {args.parsed_output_log}")
            os.remove(args.parsed_output_log)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )

    parse(args)