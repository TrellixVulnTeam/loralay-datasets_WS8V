import argparse
import os 
import shutil
import natsort
import tarfile
import time
from tqdm import tqdm 
import regex as re
from fuzzysearch import find_near_matches 
from PIL import Image, ImageDraw
import subprocess
import urllib.request
import json
from src.utils import (
    remove_processed_from_id_list, 
    compress_dir, 
    get_abstract,
    overwrite_dir_if_exists,
    del_file_if_exists
)


def find_word_idx_for_span(text, start_idx, end_idx):
    new_splitted_text = (
        text[:start_idx].split() 
        + ["<IS_ABSTRACT>"] * len(text[start_idx: end_idx].split())
        + text[end_idx:].split()
    )

    abstract_idx = [
        i for i, w in enumerate(new_splitted_text) if w == "<IS_ABSTRACT>"
    ]

    if len(abstract_idx) == 0:
        return None 

    if len(abstract_idx) == len(text.split()):
        return None

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


def _update_and_save_txt(out_txt_path, in_txt_path, start_stop_indices):
    with open(out_txt_path, "w") as fw:
        with open(in_txt_path, "r") as f:
            for i, line in enumerate(f):
                if i < start_stop_indices[0] or i > start_stop_indices[1]:
                    fw.write(line)


def _update_and_save_img(
    doc_id, 
    in_img_tar, 
    page_num, 
    start_stop_indices,
    pdf_size,
    bboxes,
    out_img_folder, 
    out_img_tar, 
):
    with tarfile.open(in_img_tar) as tar:
        tar.extractall(out_img_folder)

    doc_out_img_folder = os.path.join(out_img_folder, doc_id)
    image_page_path = os.path.join(
        doc_out_img_folder,
        f"{doc_id}-{page_num}.jpg"
    )
    image = Image.open(image_page_path)
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size
    width, height = pdf_size
    scale_w = img_width / width
    scale_h = img_height / height

    for i, box in enumerate(bboxes):
        if i >= start_stop_indices[0] and i <= start_stop_indices[1]:
            box = [int(b) for b in box]
            scaled_box = [box[0] * scale_w, box[1] * scale_h, box[2] * scale_w, box[3] * scale_h]

            draw.rectangle(scaled_box, fill="black")

    image.save(image_page_path)
    image.close()

    compress_dir(out_img_tar, doc_out_img_folder)
    shutil.rmtree(doc_out_img_folder)

def count_num_pages(filepath):
    last_line = subprocess.check_output(['tail', '-1', filepath])[:-1]
    last_line = last_line.decode("utf-8").split("\t")
    return int(last_line[-1])


def _find_and_remove_main(txt_fnames, args):
    for txt_fname in tqdm(txt_fnames):
        doc_id = txt_fname.replace(".txt", "")
        abstract_text = get_abstract(args.abstract_path, doc_id) 

        if args.abstract_thresh > 0 and len(abstract_text.split()) < args.abstract_thresh:
            print("Skipped {} (# words in abstract = {} < {})".format(
                txt_fname, len(abstract_text.split()), args.abstract_thresh
            ))
            continue 

        doc_txt_path = os.path.join(args.text_dir, txt_fname)
        doc_out_txt_path = os.path.join(args.output_text_dir, txt_fname)

        if args.img_dir is not None:
            img_tar = os.path.join(args.img_dir, doc_id + ".tar.gz")
            doc_out_img_tar = os.path.join(args.output_img_dir, doc_id + ".tar.gz")

        with open(doc_txt_path, 'r') as f:
            curr_page = []
            curr_page_num = 1

            abstract_found = False
            offset = 0

            num_pages = count_num_pages(doc_txt_path)
            pages_to_search = [1, 2, num_pages-1, num_pages] # we only look at the first two and last two pages

            for i, line in enumerate(f):
                splits = line.split("\t")
                page_num = int(splits[-1].rstrip())

                if page_num != curr_page_num: # new page
                    if curr_page_num in pages_to_search: 
                        curr_text = " ".join([content[0] for content in curr_page])
                        abstract_start_stop_indices = find_abstract_span(
                            curr_text.lower(), abstract_text.lower(), args.max_l_dist
                        )
                        if abstract_start_stop_indices is not None:
                            abstract_found = True 
                            abstract_start_stop_indices = (
                                abstract_start_stop_indices[0] + offset,
                                abstract_start_stop_indices[1] + offset,
                            )
                             
                    if abstract_found:
                        break 
                    else:
                        curr_page = [splits]
                        offset = i
                        curr_page_num = page_num
                else:
                    curr_page.append(splits)


            if not abstract_found: # abstract might be in the last page
                curr_text = " ".join([content[0] for content in curr_page])
                abstract_start_stop_indices = find_abstract_span(
                    curr_text.lower(), abstract_text.lower(), args.max_l_dist
                )
                if abstract_start_stop_indices is not None:
                    abstract_found = True 
                    abstract_start_stop_indices = (
                        abstract_start_stop_indices[0] + offset,
                        abstract_start_stop_indices[1] + offset,
                    )

        if abstract_found:
            bboxes = [line[1:5] for line in curr_page]
            pdf_size = (int(curr_page[0][5]), int(curr_page[0][6]))

            _update_and_save_txt(
                doc_out_txt_path, doc_txt_path, abstract_start_stop_indices
            )
            if args.img_dir is not None:
                _update_and_save_img(
                    doc_id, 
                    img_tar, 
                    curr_page_num, 
                    abstract_start_stop_indices, 
                    pdf_size,
                    bboxes,
                    args.output_img_dir,
                    doc_out_img_tar 
                )

            with open(args.found_output_log, "a") as f:
                f.write(doc_id + "\n")
        else:
            with open(args.failed_output_log, "a") as f:
                f.write(doc_id + "\n")


def _find_and_remove_other(txt_fnames, args):
    for txt_fname in tqdm(txt_fnames):
        doc_id = txt_fname.replace(".txt", "")
        url = "https://api.archives-ouvertes.fr/search/" \
            f"?q=docid:{doc_id}&" \
            "wt=json&" \
            "indent=True&" \
            f"fl=abstract_s,{args.main_lang}_abstract_s" 
        response = urllib.request.urlopen(url).read().decode()
        data = json.loads(response)
        all_abstracts = data["response"]["docs"][0]["abstract_s"]
        main_abstract = data["response"]["docs"][0][args.main_lang + "_abstract_s"][0]

        doc_txt_path = os.path.join(args.text_dir, txt_fname)
        doc_out_txt_path = os.path.join(args.output_text_dir, txt_fname)
        if args.img_dir is not None:
            img_tar = os.path.join(args.img_dir, doc_id + ".tar.gz")
            doc_out_img_tar = os.path.join(args.output_img_dir, doc_id + ".tar.gz")

        if len(all_abstracts) == 1:
            shutil.copyfile(doc_txt_path, doc_out_txt_path)
            continue 

        all_abstracts = [abstract for abstract in all_abstracts if abstract != main_abstract]
        all_abstracts = [abstract_text.replace("\n", "") for abstract_text in all_abstracts]

        all_abstracts_start_stop_indices = [None for _ in all_abstracts]
        all_abstracts_found = [False for _ in all_abstracts]
        all_abstracts_page = [None for _ in all_abstracts]

        with open(doc_txt_path, 'r') as f:
            curr_page = []
            curr_page_num = 1

            offset = 0

            num_pages = count_num_pages(doc_txt_path)
            pages_to_search = [1, 2, num_pages-1, num_pages] # we only look at the first two and last two pages

            for i, line in enumerate(f):
                splits = line.split("\t")
                page_num = int(splits[-1].rstrip())

                if page_num != curr_page_num: # new page
                    if curr_page_num in pages_to_search: 
                        curr_text = " ".join([content[0] for content in curr_page])
                        for lang_idx, abstract_text in enumerate(all_abstracts):
                            abstract_start_stop_indices = find_abstract_span(
                                curr_text.lower(), abstract_text.lower(), args.max_l_dist
                            )
                            if abstract_start_stop_indices is not None:
                                all_abstracts_found[lang_idx] = True 
                                all_abstracts_start_stop_indices[lang_idx] = (
                                    abstract_start_stop_indices[0] + offset,
                                    abstract_start_stop_indices[1] + offset,
                                )
                                all_abstracts_page[lang_idx] = (curr_page_num, curr_page)
                            
                    if all(all_abstracts_found):
                        break 
                    else:
                        curr_page = [splits]
                        offset = i
                        curr_page_num = page_num
                else:
                    curr_page.append(splits)


            if not all(all_abstracts_found): # abstract might be in the last page
                curr_text = " ".join([content[0] for content in curr_page])
                for lang_idx, abstract_text in enumerate(all_abstracts):
                    abstract_start_stop_indices = find_abstract_span(
                        curr_text.lower(), abstract_text.lower(), args.max_l_dist
                    )
                    if abstract_start_stop_indices is not None:
                        all_abstracts_found[lang_idx] = True
                        all_abstracts_start_stop_indices[lang_idx] = (
                            abstract_start_stop_indices[0] + offset,
                            abstract_start_stop_indices[1] + offset,
                        )
                        all_abstracts_page[lang_idx] = (curr_page_num, curr_page)

        if all(all_abstracts_found):
            for lang_idx in range(len(all_abstracts)):
                page_num, page = all_abstracts_page[lang_idx]
                abstract_start_stop_indices = all_abstracts_start_stop_indices[lang_idx]
                bboxes = [line[1:5] for line in page]
                pdf_size = (int(page[0][5]), int(page[0][6]))

                _update_and_save_txt(
                    doc_out_txt_path, doc_txt_path, abstract_start_stop_indices
                )
                if args.img_dir is not None:
                    _update_and_save_img(
                        doc_id, 
                        img_tar, 
                        page_num, 
                        abstract_start_stop_indices, 
                        pdf_size,
                        bboxes,
                        args.output_img_dir,
                        doc_out_img_tar 
                    )

            with open(args.found_output_log, "a") as f:
                f.write(doc_id + "\n")
        else:
            with open(args.failed_output_log, "a") as f:
                f.write(doc_id + "\n")

        # time.sleep(1)

def find_and_remove(args):
    txt_fnames = sorted(os.listdir(args.text_dir))
    txt_fnames = txt_fnames[:args.n_docs] if args.n_docs > 0 else txt_fnames 

    if args.resume_processing:
        txt_fnames = [fname[:-len(".txt")] for fname in txt_fnames]
        print("Resuming processing...")
        txt_fnames = remove_processed_from_id_list(
            txt_fnames, args.found_output_log, args.failed_output_log
        )
        if not txt_fnames:
            print(f"All documents in {args.text_dir} have already been processed.")
            return 
        txt_fnames = [fname + ".txt" for fname in txt_fnames]

    if not args.remove_other_lang:
        _find_and_remove_main(txt_fnames, args)
    else:
        _find_and_remove_other(txt_fnames, args)

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
        "--abstract_path",
        default=None,
        type=str,
    )
    parser.add_argument(
        "--img_dir",
        default=None,
        type=str,
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
    )
    parser.add_argument(
        "--main_lang",
        default=None,
        type=str,
    )
    parser.add_argument(
        "--remove_other_lang", 
        action="store_true", 
        help="Remove abstracts in other languages."
    )
    parser.add_argument(
        "--n_docs", 
        type=int,
        default=5,
    )
    parser.add_argument(
        "--abstract_thresh", 
        type=int,
        default=-1,
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
            overwrite_dir_if_exists(args.output_text_dir)
            if args.img_dir is not None: 
                overwrite_dir_if_exists(args.output_img_dir)
            del_file_if_exists(args.found_output_log)
            del_file_if_exists(args.failed_output_log)
        else:
            if os.listdir(args.output_text_dir):
                raise ValueError(
                    f"Output directory ({args.output_text_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if args.img_dir is not None and os.listdir(args.output_img_dir):
                raise ValueError(
                    f"Output directory ({args.output_img_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            

    find_and_remove(args)