import argparse 
import os 
import shutil
import subprocess
import tarfile 
import xml.etree.ElementTree as ET
import urllib.request
from utils import get_ids

def extract_abstract(url):
    response = urllib.request.urlopen(url).read()
    tree = ET.fromstring(response)
    abstract_nodes = tree.findall(".//passage[infon = 'ABSTRACT']/text")
    if not abstract_nodes:
        return None 
    else:
        abstract_text = " ".join(a.text for a in abstract_nodes)
        return abstract_text

def extract_pdf_from_pdf_url(url, output_path):
    command = f"wget -O {output_path} {url}"
    subprocess.call(command, shell=True)
    
    if os.path.exists(output_path):
        return True
    return False 

def extract_pdf_from_tar_url(url, output_path, tar_path):
    command = f"wget -O {tar_path} {url}"
    subprocess.call(command, shell=True)

    tar = tarfile.open(tar_path)
    pdf_fname = [t.name for t in tar.getmembers() if ".pdf" in t.name]

    if len(pdf_fname) == 1:
        pdf_contents = tar.extractfile(pdf_fname[0]).read()
        with open(output_path, "wb") as fw:
            fw.write(pdf_contents)
        os.remove(tar_path)
        return True 
    return False 

def find_ft_url(oa_url):
    response = urllib.request.urlopen(oa_url).read()
    tree = ET.fromstring(response)

    links = tree.findall(".//link")    
    if len(links) > 1:
        return tree.find('.//link[@format="pdf"]').get("href")
    else:
        return links[0].get("href")

def extract(args):
    id_list = get_ids(args.input_file, args.n_docs)
    id_failed = []
    for pmcid in id_list:
        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
        ft_url = find_ft_url(oa_url)
        output_path = os.path.join(args.pdf_output_dir, pmcid + ".pdf")
        if ".pdf" in ft_url:
            pdf_extracted = extract_pdf_from_pdf_url(ft_url, output_path)
        else:
            tar_path = os.path.join(args.tmp_output_dir, pmcid + ".tar.gz")

            pdf_extracted = extract_pdf_from_tar_url(ft_url, output_path, tar_path)
        
        abstract_text = extract_abstract(
            f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmcid}/unicode"
        )

        if abstract_text: 
            if pdf_extracted: # abstract and pdf exist: save abstract
                with open(
                    os.path.join(args.abstract_output_dir, pmcid + ".txt"), "w"
                ) as fw:
                    abstract_words = abstract_text.strip().split()
                    for w in abstract_words:
                        fw.write(w + "\n")
            else: 
                id_failed.append((pmcid, 'pdf'))
        else:
            id_failed.append((pmcid, 'abstract'))
            if pdf_extracted: # pdf has been extracted, delete it
                os.remove(output_path)

    if id_failed:
        print("Failed to extract following files: ", id_failed)

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
        "--tmp_output_dir", 
        type=str,
        default="./tmp",
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

    if os.listdir(args.pdf_output_dir):
        if args.overwrite_output_dir:
            print(f"Overwriting {args.pdf_output_dir}")
            shutil.rmtree(args.pdf_output_dir)
            os.makedirs(args.pdf_output_dir)
        else:
            raise ValueError(
                f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )

    extract(args)