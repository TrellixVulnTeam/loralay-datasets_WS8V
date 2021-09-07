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

For ArXiv, raw abstracts are contained in a separate metadatafile (downloaded from https://www.kaggle.com/Cornell-University/arxiv). For PubMed, they are retrieved using the PMC OAI service. 


To extract from ArXiv:
~~~shell
$ python extract_from_arxiv.py --input_file path/to/original/data/file \
                               --metadata_file path/to/metadata/file \
                               --pdf_output_dir path/to/pdf/output/dir \
                               --abstract_output_path path/to/abstract/output/file \
                               --n_docs num_docs_to_process # -1 to process every document
~~~

To extract from PubMed:
~~~shell
$ python extract_from_pubmed.py --input_file path/to/original/data/file \
                                --pdf_output_dir path/to/pdf/output/dir \
                                --abstract_output_path path/to/abstract/output/file \
                                --n_docs num_docs_to_process # -1 to process every document
~~~

## Convert PDFs to images

~~~shell
$ python convert_pdf_to_image.py --input_dir path/to/pdf/dir \
                                 --output_dir path/to/img/dir \
                                 --n_docs num_docs_to_process # -1 to process every document
~~~

## Convert PDFs to HTMLs

~~~shell
$ python convert_pdf_to_html.py --input_dir path/to/dir/containing/pdf/folder \
                                --pdf_folder pdf/folder \
                                --output_folder html/folder \
                                --n_docs num_docs_to_process # -1 to process every document
~~~

## Convert HTMLs to txt

~~~shell
$ python parse_html.py --html_dir path/to/html/dir \
                       --output_dir path/to/txt/output/dir \
                       --n_docs num_docs_to_process # -1 to process every document
~~~

## Find and remove abstract from texts and images

~~~
$ python find_and_remove_abstract.py --text_dir path/to/txt/dir \
                                     --abstract_dir path/to/abstract/dir \
                                     --img_dir path/to/img/dir \
                                     --output_text_dir path/to/output/text/dir \
                                     --output_img_dir path/to/output/text/dir \
                                     --n_docs num_docs_to_process # -1 to process every document
~~~

