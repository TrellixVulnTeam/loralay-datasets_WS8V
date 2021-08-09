# Summarization datasets with layout and image information

## Environment Setup 

~~~shell
$ conda create -n summ-datasets python=3.8
$ conda activate summ-datasets 
$ git clone ssh://git@source.recital.ai:2222/research/doc-intelligence/summ-datasets.git
$ cd summ-datasets
$ pip install -r requirements.txt
~~~

## Extract PDF files from ArXiv and PubMed datasets

PDFs are extracted based on IDs contained in the original data files (downloaded from https://github.com/armancohan/long-summarization). 

Raw abstracts are retrieved using OAI-PMH for arXiv, and the PMC OAI service for PubMed. 

To extract from ArXiv:
~~~shell
$ python extract_from_arxiv.py --input_file path/to/original/data/file \
                               --pdf_output_dir path/to/pdf/output/dir \
                               --abstract_output_dir path/to/abstract/output/dir \
~~~

To extract from PubMed:
~~~shell
$ python extract_from_pubmed.py --input_file path/to/original/data/file \
                                --pdf_output_dir path/to/pdf/output/dir \
                                --abstract_output_dir path/to/abstract/output/dir \
~~~

## Convert PDFs to images

~~~shell
$ python convert_pdf_to_image.py --input_dir path/to/pdf/dir \
                                 --output_dir path/to/img/dir \
~~~

## Convert PDFs to HTMLs

~~~shell
$ python convert_pdf_to_html.py --input_dir path/to/dir/containing/pdf/folder \
                                --pdf_folder pdf/folder \
                                --output_folder html/folder \
~~~

## Convert HTMLs to txt

~~~shell
$ python parse_html.py --html_dir path/to/html/dir \
                       --output_dir path/to/txt/output/dir \
~~~

## Find and remove abstract from texts and images

~~~
$ python find_and_remove_abstract.py --text_dir path/to/txt/dir \
                                     --img_dir path/to/img/dir \
                                     --output_img_dir path/to/img/dir \
~~~

