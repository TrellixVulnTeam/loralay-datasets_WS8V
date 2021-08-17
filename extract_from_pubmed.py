import argparse 
import os 
import shutil
import subprocess
import tarfile 
import xml.etree.ElementTree as ET
import urllib.request
from utils import get_ids

def extract_abstract(url):
    """ Extract abstract using the BioC API

    Args:
        url (string): URL of article abstract in BioC XML format

    Returns:
        string: Abstract text 
    """
    response = urllib.request.urlopen(url).read()
    tree = ET.fromstring(response)
    abstract_nodes = tree.findall(".//passage[infon = 'ABSTRACT']/text")
    if not abstract_nodes:
        return None 
    else:
        abstract_text = " ".join(a.text for a in abstract_nodes)
        return abstract_text

def extract_pdf_from_pdf_url(url, output_path):
    """ Extract PDF based on FTP link (https://www.ncbi.nlm.nih.gov/pmc/tools/ftp/)

    Args:
        url (string): FTP link to PDF 
        output_path (string): Path to output PDF file

    Returns:
        bool: True if extraction was successful, False otherwise
    """
    command = f"wget -O {output_path} {url}"
    subprocess.call(command, shell=True)
    
    if os.path.exists(output_path):
        return True
    return False 

def extract_pdf_from_tar_url(url, output_path, tar_path):
    """ Extract PDF from tar archive 

    Args:
        url (string): FTP link to tar archive containing PDF
        output_path (string): Path to output PDF file
        tar_path (string): Path to tar archive

    Returns:
        bool: True if extraction was successful, False otherwise
    """
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

def find_ftp_url(oa_url):
    """ Extract FTP URL from PMC OA URL (https://www.ncbi.nlm.nih.gov/pmc/tools/ftp/)

    Args:
        oa_url (string): OA URL providing the article location on the FTP site 

    Returns:
        string: link to the article (PDF or tar) location on the FTP site
    """
    response = urllib.request.urlopen(oa_url).read()
    tree = ET.fromstring(response)

    links = tree.findall(".//link")    
    if len(links) > 1:
        return tree.find('.//link[@format="pdf"]').get("href")
    else:
        return links[0].get("href")

def remove_downloaded_from_id_list(args, id_list):
    """ Remove already downloaded articles and articles that could not be downloaded

    Args:
        args (Namespace): command line arguments
        id_list (list): list of PMCIDs  

    Returns:
        list: list of PMCIDs whose articles have not been downloaded yet
    """
    if os.path.isfile(args.failed_output_file):
        with open(args.failed_output_file, "r") as f:
            failed_to_download = f.read().splitlines()
    else:
        failed_to_download = []

    if os.path.isfile(args.downloaded_output_file):
        with open(args.downloaded_output_file, "r") as f:
            downloaded = f.read().splitlines()
    else:
        downloaded = []

    id_list = [
        pmcid for pmcid in id_list if (
            pmcid not in failed_to_download and pmcid not in downloaded
        )
    ] # remove pmcids whose articles could not be downloaded or whose have already been downloaded
    return id_list

def extract(args):
    id_list = get_ids(args.input_file, args.n_docs)

    if args.resume_download:
        id_list = remove_downloaded_from_id_list(args, id_list)

        if not id_list:
            print(f"All articles in {args.input_file} have already been extracted")
            return 

    print(f"Extracting {len(id_list)} articles from PubMed, using IDs in {args.input_file}")
    
    for pmcid in id_list:
        failed_extraction = False

        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
        ftp_url = find_ftp_url(oa_url)
        output_path = os.path.join(args.pdf_output_dir, pmcid + ".pdf")
        if ".pdf" in ftp_url:
            pdf_extracted = extract_pdf_from_pdf_url(ftp_url, output_path)
        else:
            tar_path = os.path.join(args.tmp_output_dir, pmcid + ".tar.gz")

            pdf_extracted = extract_pdf_from_tar_url(ftp_url, output_path, tar_path)
        
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
                failed_extraction = True
        else:
            failed_extraction = True
            if pdf_extracted: # pdf has been extracted, delete it
                os.remove(output_path)

        if failed_extraction:
            with open(args.failed_output_file, "a") as f:
                f.write(pmcid + "\n")
        else:
            with open(args.downloaded_output_file, "a") as f:
                f.write(pmcid + "\n")
        

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
        "--downloaded_output_file",
        type=str,
        default="./downloaded.txt"
    )
    parser.add_argument(
        "--failed_output_file",
        type=str,
        default="./failed_to_download.txt"
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

    if os.listdir(args.pdf_output_dir) and not args.resume_download:
        if args.overwrite_output_dir:
            for output_dir in [
                args.pdf_output_dir, args.abstract_output_dir, args.tmp_output_dir
            ]:
                print(f"Overwriting {output_dir}")
                shutil.rmtree(output_dir)
                os.makedirs(output_dir)

            print(f"Overwriting {args.downloaded_output_file}")
            os.remove(args.downloaded_output_file)
            print(f"Overwriting {args.failed_output_file}")
            os.remove(args.failed_output_file)
        else:
            if os.listdir(args.pdf_output_dir):
                raise ValueError(
                    f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.listdir(args.abstract_output_dir):
                raise ValueError(
                    f"Output directory ({args.abstract_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.listdir(args.tmp_output_dir):
                raise ValueError(
                    f"Output directory ({args.tmp_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.path.isfile(args.downloaded_output_file):
                raise ValueError(
                    f"Output file ({args.downloaded_output_file}) already exists. Use --overwrite_output_dir to overcome."
                )
            if os.path.isfile(args.failed_output_file):
                raise ValueError(
                    f"Output file ({args.failed_output_file}) already exists. Use --overwrite_output_dir to overcome."
                )


    extract(args)