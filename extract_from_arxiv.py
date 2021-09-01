
import argparse
import time
import os
import shutil
import subprocess
from subprocess import PIPE
import re
import xml.etree.ElementTree as ET
import urllib.request 
from tqdm import tqdm
from utils import get_ids, remove_processed_from_id_list


def matches_first_id_scheme(id):
    """ Checks if id matches identifier scheme used until March 2007 
            e.g. astro-ph9702020

    Args:
        id (string): arXiv identifier 

    Returns:
        bool: True if id matches scheme, False otherwise
    """
    p = re.compile("^([a-z\-]*)(\d{7})$")
    m = p.match(id)
    return m

def extract_pdf(arxiv_id, pdf_output_path):
    """ Extract PDF from Google Cloud Storage buckets using gsutil

    Args:
        arxiv_id (string): arXiv identifier
        pdf_output_path (string): Path to output PDF 

    Returns:
        bool: True if PDF has been correctly extracted, False otherwise
    """
    m = matches_first_id_scheme(arxiv_id)
    if m:
        command = [
            "gsutil", 
            "ls",
            f"gs://arxiv-dataset/arxiv/{m.group(1)}/pdf/{m.group(2)[:4]}/{m.group(2)}v*.pdf"
        ]
    else:
        p = re.compile("^(\d{4})\.(\d{4,5})$")
        m = p.match(arxiv_id)
        assert m, print(arxiv_id)
        command = [
            "gsutil",
            "ls",
            f"gs://arxiv-dataset/arxiv/arxiv/pdf/{m.group(1)}/{arxiv_id}v*.pdf"
        ]

    p = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()

    versions = output.decode("utf-8").split("\n")
    versions = [v for v in versions if v] # remove empty string
    print(versions)
    if m:
        sorted_versions = sorted(
            versions, 
            key=lambda x: int(re.match(".*" + re.escape(m.group(2)) + "v([0-9]+).pdf", x).group(1))
        )
    else:
        sorted_versions = sorted(
            versions, 
            key=lambda x: int(re.match(".*" + re.escape(arxiv_id) + "v([0-9]+).pdf", x).group(1))
        )

    command = f"gsutil cp {sorted_versions[-1]} {pdf_output_path}"

    subprocess.call(command, shell=True)

    if os.path.exists(pdf_output_path):
        return True 
    return False

def extract_abstract(url):
    """ Extract abstract using OAI-PMH

    Args:
        url (string): URL providing metadata for an article 

    Returns:
        string: Text from abstract
    """
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

    if args.resume_download:
        id_list = remove_processed_from_id_list(
            id_list, args.downloaded_output_log, args.failed_output_log
        )

        if not id_list:
            print(f"All articles in {args.input_file} have already been extracted")
            return 

    print(f"Extracting {len(id_list)} articles from arXiv, using IDs in {args.input_file}")

    start = None

    for arxiv_id in id_list:
        failed_extraction = False

        pdf_output_path = os.path.join(args.pdf_output_dir, arxiv_id + ".pdf")
        pdf_extracted = extract_pdf(arxiv_id, pdf_output_path)

        m = matches_first_id_scheme(arxiv_id)
        if m:
            url = f"http://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:{m.group(1)}/{m.group(2)}&metadataPrefix=arXiv"
        else:
            url = f"http://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:{arxiv_id}&metadataPrefix=arXiv"
        
        
        if start:
            stop = time.time()
            time_between_requests = stop - start 
            if time_between_requests < 3:
                time.sleep(3 - time_between_requests)

        abstract_text = extract_abstract(url)
        start = time.time()

        if abstract_text: 
            if pdf_extracted: # abstract and pdf exist: save abstract
                abstract_output_path = os.path.join(args.abstract_output_dir, arxiv_id + ".txt")
                with open(abstract_output_path, "w") as fw:
                    abstract_words = abstract_text.strip().split()
                    for w in abstract_words:
                        fw.write(w + "\n")
            else: 
                failed_extraction = True
        else:
            failed_extraction = True
            if pdf_extracted: # pdf has been extracted, delete it
                os.remove(pdf_output_path)
        
    
        if failed_extraction:
            with open(args.failed_output_log, "a") as f:
                f.write(arxiv_id + "\n")
        else:
            with open(args.downloaded_output_log, "a") as f:
                f.write(arxiv_id + "\n")


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
        "--downloaded_output_log",
        type=str,
        default="./downloaded.log"
    )
    parser.add_argument(
        "--failed_output_log",
        type=str,
        default="./failed_to_download.log"
    )
    parser.add_argument(
        "--n_docs",
        type=int,
        default=5,
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

    if (os.listdir(args.pdf_output_dir) or os.listdir(args.abstract_output_dir)) and not args.resume_download:
        if args.overwrite_output_dir:
            print(f"Overwriting {args.pdf_output_dir}")
            shutil.rmtree(args.pdf_output_dir)
            os.makedirs(args.pdf_output_dir)
            print(f"Overwriting {args.abstract_output_dir}")
            shutil.rmtree(args.abstract_output_dir)
            os.makedirs(args.abstract_output_dir)

            print(f"Overwriting {args.downloaded_output_log}")
            os.remove(args.downloaded_output_log)
            if os.path.isfile(args.failed_output_log):
                print(f"Overwriting {args.failed_output_log}")
                os.remove(args.failed_output_log)
        else:
            if os.listdir(args.pdf_output_dir):
                raise ValueError(
                    f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.listdir(args.abstract_output_dir):
                raise ValueError(
                    f"Output directory ({args.abstract_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.path.isfile(args.downloaded_output_log):
                raise ValueError(
                    f"Output file ({args.downloaded_output_log}) already exists. Use --overwrite_output_dir to overcome."
                )
            if os.path.isfile(args.failed_output_log):
                raise ValueError(
                    f"Output file ({args.failed_output_log}) already exists. Use --overwrite_output_dir to overcome."
                )

    extract(args)