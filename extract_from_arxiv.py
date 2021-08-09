
import argparse
import time
import os
import shutil
import subprocess
import re
import xml.etree.ElementTree as ET
import urllib.request 
from tqdm import tqdm
from utils import get_abstracts, get_ids


def matches_first_id_scheme(id):
    p = re.compile("^([a-z\-]*)(\d{7})$")
    m = p.match(id)
    return m

def extract_pdf(arxiv_id, pdf_output_path):
    m = matches_first_id_scheme(arxiv_id)
    if m:
        command = "gsutil cp gs://arxiv-dataset/arxiv/" \
            f"{m.group(1)}/pdf/{m.group(2)[:4]}/{m.group(2)}v1.pdf " \
            f"{pdf_output_path}"
    else:
        p = re.compile("^(\d{4})\.(\d{4,5})$")
        m = p.match(arxiv_id)
        assert m, print(arxiv_id)
        command = "gsutil cp gs://arxiv-dataset/arxiv/" \
            f"arxiv/pdf/{m.group(1)}/{arxiv_id}v1.pdf " \
            f"{pdf_output_path}"

    subprocess.call(command, shell=True)

    if os.path.exists(pdf_output_path):
        return True 
    return False

def extract_abstract(url):
    response = urllib.request.urlopen(url).read()
    tree = ET.fromstring(response)
    if not tree:
        return None 
    print(url)    
    node = tree.find(
        ".//pns:metadata", 
        namespaces={"pns": "http://www.openarchives.org/OAI/2.0/"}
    ).getchildren()[0]
    if not node:
        return None
    
    abstract_text = node.find(
        "./pns:abstract", 
        namespaces={"pns": "http://arxiv.org/OAI/arXiv/"}
    ).text

    return abstract_text


def extract(args):
    id_list = get_ids(args.input_file, args.n_docs)
    id_failed = []
    start = time.time()

    for arxiv_id in id_list:
        pdf_output_path = os.path.join(args.pdf_output_dir, arxiv_id + ".pdf")
        pdf_extracted = extract_pdf(arxiv_id, pdf_output_path)

        m = matches_first_id_scheme(arxiv_id)
        if m:
            url = f"http://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:{m.group(1)}/{m.group(2)}&metadataPrefix=arXiv"
        else:
            url = f"http://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:{arxiv_id}&metadataPrefix=arXiv"
        abstract_text = extract_abstract(url)

        if abstract_text: 
            if pdf_extracted: # abstract and pdf exist: save abstract
                with open(
                    os.path.join(args.abstract_output_dir, arxiv_id + ".txt"), "w"
                ) as fw:
                    abstract_words = abstract_text.strip().split()
                    for w in abstract_words:
                        fw.write(w + "\n")
            else: 
                id_failed.append((arxiv_id, 'pdf'))
        else:
            id_failed.append((arxiv_id, 'abstract'))
            if pdf_extracted: # pdf has been extracted, delete it
                os.remove(pdf_output_path)

        

    if id_failed:
        print(f"Failed to retrieve:")
        for arxiv_id, reason in id_failed:
            print(f"\t{arxiv_id} ({reason})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--pdf_output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--abstract_output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--n_docs",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if os.listdir(args.pdf_output_dir) or os.listdir(args.abstract_output_dir):
        if args.overwrite_output_dir:
            print(f"Overwriting {args.pdf_output_dir}")
            shutil.rmtree(args.pdf_output_dir)
            os.makedirs(args.pdf_output_dir)
            print(f"Overwriting {args.abstract_output_dir}")
            shutil.rmtree(args.abstract_output_dir)
            os.makedirs(args.abstract_output_dir)
        else:
            if os.listdir(args.pdf_output_dir):
                raise ValueError(
                    f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.listdir(args.abstract_output_dir):
                raise ValueError(
                    f"Output directory ({args.abstract_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )

    extract(args)