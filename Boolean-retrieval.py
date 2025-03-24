import os
import re
import streamlit as st
import nltk
import wordninja
from collections import defaultdict
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

nltk.download('punkt')
nltk.download('stopwords')

porter_stemmer = PorterStemmer()

#""" in this func the query is undergone the following steps:
#    1. tokenize, 
#    2. converted to lowercase,
#    3. stopwords are removed using stopwords.txt file as well as nltk,
#    4. URLS, punctuations, and filtering
#    5. stemming using porter stemmer
#"""
def preprocess_text(text, stopwords_file):
    text = text.lower()
    tokens = word_tokenize(text)
    
    # Filtering tokens by removing URLs, punctuation, and splitting long words
    filtered_tokens = []
    for token in tokens:
        if not token.startswith("http://") and not token.startswith("https://"):
            if re.match("^[^\W\d_]+$", token):
                if len(token) > 10:
                    processed_words = split_words([token])
                    filtered_tokens.extend(processed_words)
                else:
                    filtered_tokens.append(token)
    
    # Remove stopwords
    with open(stopwords_file, 'r') as file:
        custom_stopwords = file.read().splitlines()

    nltk_stopwords = set(stopwords.words('english'))
    all_stopwords = set(custom_stopwords + list(nltk_stopwords))
    filtered_tokens = [token for token in filtered_tokens if token not in all_stopwords]
    
    # Perform stemming
    stemmer = PorterStemmer()
    stemmed_tokens = [stemmer.stem(token) for token in filtered_tokens]
    
    return stemmed_tokens

def split_words(word_list):
    new_word_list = []
    for word in word_list:
        if len(word) > 10:
            split_words = wordninja.split(word)
            new_word_list.extend(split_words)
        else:
            new_word_list.append(word)
    return new_word_list

#""" making inverted index by receiving a collection of txt files reading them in a loop one by one
#    and sending the txt file to the preprocess function for preprocessing 
#    and finally add the tokens in the inverted index
#"""
def inverted_ind(directories, stopwords_file):
    inverted_index = defaultdict(set)
    for directory in directories:
        for filename in os.listdir(directory):
            try:
                with open(os.path.join(directory, filename), 'r') as file:
                    text = file.read()
                    tokens = preprocess_text(text, stopwords_file)
                    for token in tokens:
                        inverted_index[token].add(filename)
            except UnicodeDecodeError:
                print(f"Error reading file: {filename}")
    return inverted_index

#""" making pos index by receiving a collection of txt files, reading them in a loop one by one
#    and sending the txt file to the preprocess function for preprocessing 
#    and finally add the tokens and their positions in the positional index
#    i have not included stopwords in the index
#"""
def positional_ind(directories, stopwords_file):
    positional_index = defaultdict(lambda: defaultdict(list))
    for directory in directories:
        for filename in os.listdir(directory):
            try:
                with open(os.path.join(directory, filename), 'r') as file:
                    text = file.read()
                    tokens = preprocess_text(text, stopwords_file)
                    for position, token in enumerate(tokens):
                        positional_index[token][filename].append(position)
            except UnicodeDecodeError:
                print(f"Error reading file: {filename}")
    return positional_index

#""" this func is called from the main func with attributes indexes and user query
#    it first break the query into terms(by calling function preprocessing)
#    check for the proximity operator, if present call func for positional processing
#    otherwise retrieved documents satisfying the boolean query
#"""
def process_boolean_query(query, inverted_index, positional_index, stopwords_file):
    query_terms = preprocess_text(query, stopwords_file)
    result_docs = None
    not_flag = False
    positional_query_flag = False

    if "/" in query:
        positional_query_flag = True

    if positional_query_flag:
        return process_positional_query(positional_index, query)
    else:
        for term in query_terms:
            if term == "and":
                next_term = query_terms[query_terms.index(term) + 1]
                doc_ids = set(inverted_index.get(next_term, set()))
                result_docs = result_docs.intersection(doc_ids) if result_docs is not None else doc_ids
            elif term == "or":
                next_term = query_terms[query_terms.index(term) + 1]
                doc_ids = set(inverted_index.get(next_term, set()))
                result_docs = result_docs.union(doc_ids) if result_docs is not None else doc_ids
            elif term == "not":
                not_flag = True
            else:
                if not_flag:
                    result_docs = result_docs.difference(inverted_index.get(term, set()))
                    not_flag = False
                else:
                    doc_ids = set(inverted_index.get(term, set()))
                    result_docs = doc_ids if result_docs is None else result_docs.intersection(doc_ids)
        if result_docs is None:
            result_docs = set()
        return result_docs

#""" it first break the query into terms(splitting by /)
#    store proximity value and stemmed the terms by porter stemmer
#    find the positions of term in documents
#    i have considered k(proximity value) as a max value not exact 
#"""
def process_positional_query(positional_index, query):
    query_parts = query.split('/')
    query_terms = query_parts[0].split() 
    k = int(query_parts[1].strip()) 

    terms = [porter_stemmer.stem(term) for term in query_terms]  

    t1 = terms[0]
    t2 = terms[1]

    result_docs = set()
    t1_pos = positional_index.get(t1, {})
    t2_pos = positional_index.get(t2, {})

    for doc_id in set(t1_pos.keys()) & set(t2_pos.keys()):
        doc_pos_t1 = t1_pos[doc_id]
        doc_pos_t2 = t2_pos[doc_id]

        for pos_t1 in doc_pos_t1:
            for pos_t2 in doc_pos_t2:
                if 0 < abs(pos_t1 - pos_t2) <= k: 
                    result_docs.add(doc_id)
                    break 

    return result_docs

def main():
    st.title("Boolean Retrieval Model")

    index_type = st.radio("Choose index type:", ["Inverted Index", "Positional Index"])

    query = st.text_input("Enter query:")

    if st.button("Execute Query"):
        directories = [r"C:\Users\user\Documents\6th semester\IR\ResearchPapers"]
        stopwords = r"C:\Users\user\Documents\6th semester\IR\Stopword-List.txt"

        if index_type == "Inverted Index":
            inverted_index = inverted_ind(directories, stopwords)
            positional_index = positional_ind(directories, stopwords)
            result = process_boolean_query(query, inverted_index, positional_index, stopwords)
        else:
            inverted_index = inverted_ind(directories, stopwords)
            positional_index = positional_ind(directories, stopwords)
            result = process_boolean_query(query, inverted_index, positional_index, stopwords)

        if result:
            st.write("Query Result:")
            for doc in result:
                st.write(doc)
        else:
            st.write("No documents found.")

if __name__ == "__main__":
    main()
