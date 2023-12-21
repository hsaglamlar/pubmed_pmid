""" This script parses the XML file of the article and 
yields the dictionary of the article types info"""
import gzip

from lxml import etree
import pandas as pd


def get_article_type_info(xml_tree):
    """Get the article info from the XML tree
    Args:
        xml_tree (Element): The lxml node pointing to a medline document
    Returns:
        dict: A dictionary containing the pm_id and the publication types of the article
    """
    article_type_info = {}

    pmid = xml_tree.find(".//PMID")
    article_type_info["pmid"] = pmid.text if pmid is not None else None

    # get pmc_id
    pmc_id = xml_tree.find(".//ArticleId[@IdType='pmc']")
    article_type_info["pmc_id"] = pmc_id.text if pmc_id is not None else None

    # Get the article publication type
    type_infos = xml_tree.findall(".//PublicationTypeList/PublicationType")
    article_type_info["publication_type"] = ""
    if len(type_infos) > 0:
        article_type_info["publication_type"] = [
            (type_info.attrib.get("UI", None), type_info.text)
            for type_info in type_infos
        ]

    return article_type_info


def parse_pubmed_xml_iter(path):
    """Parse the XML file of the article and yield the dictionary of the article types info
    Args:
        path (str): The path to the XML GZ file of the article
    Yields:
        dict: A dictionary containing the pm_id and the publication types of the article
    """
    with gzip.open(path, "rb") as f:
        for _, element in etree.iterparse(f, events=("end",)):
            if element.tag == "PubmedArticle":
                res = get_article_type_info(xml_tree=element)
                element.clear()
                yield res

def get_article_type_csv(input_path, output_csv_path):
    """Parse the XML file of the article and 
    save the dictionary of the article types info as a CSV file
    Args:
        input_path (str): The path to the XML GZ file of the article
        output_csv_path (str): The path to the CSV file to save the results
    """
    # iterate over the generator and store the results in a list
    article_type_list = []
    for article in parse_pubmed_xml_iter(input_path):
        if article is None:
            continue
        article_type_list.append(article)

    # convert the list of dictionaries to a pandas dataframe and save it as a CSV file
    df = pd.DataFrame(article_type_list)
    df.to_csv(output_csv_path, index=False)


if __name__ == "__main__":
    INPUT_PATH = "./data/pubmed23n1181.xml.gz"
    OUTPUT_CSV_PATH = "./data/pubmed23n1181.csv"

    print("Parsing XML file...", INPUT_PATH)
    get_article_type_csv(INPUT_PATH, OUTPUT_CSV_PATH)
    print("Done! The results are saved in the CSV file:", OUTPUT_CSV_PATH)
