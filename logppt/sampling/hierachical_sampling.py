import json
import os
import pandas as pd
import re
import string
from sklearn.utils import shuffle
import textdistance
import random
import heapq
from collections import Counter, defaultdict, deque, OrderedDict
from sklearn.feature_extraction._stop_words import ENGLISH_STOP_WORDS
import time
import calendar
import argparse
import numpy as np
from copy import deepcopy

# from . import datasets, benchmark

def generate_logformat_regex(log_format):
    """ Function to generate regular expression to split log messages
    """
    headers = []
    splitters = re.split(r'(<[^<>]+>)', log_format)
    regex = ''
    for k in range(len(splitters)):
        if k % 2 == 0:
            splitter = re.sub(' +', '\\\s+', splitters[k])
            regex += splitter
        else:
            header = splitters[k].strip('<').strip('>')
            regex += '(?P<%s>.*?)' % header
            headers.append(header)
    regex = re.compile('^' + regex + '$')
    return headers, regex


def log_to_dataframe(log_file, log_format):
    """ Function to transform log file to dataframe
    """
    headers, regex = generate_logformat_regex(log_format)
    log_messages = []
    line_count = 0
    with open(log_file, 'r', encoding='utf8', errors='ignore') as fin:
        for line in fin.readlines():
            try:
                match = regex.search(line.strip())
                message = [match.group(header) for header in headers]
                log_messages.append(message)
                line_count += 1
            except Exception as _:
                pass
    logdf = pd.DataFrame(log_messages, columns=headers)
    logdf.insert(0, 'LineId', None)
    logdf['LineId'] = [i + 1 for i in range(line_count)]
    return logdf


def lcs_distance(x, y):
    seq1 = x.split()
    seq2 = y.split()
    lengths = [[0 for j in range(len(seq2) + 1)] for i in range(len(seq1) + 1)]
    # row 0 and column 0 are initialized to 0 already
    for i in range(len(seq1)):
        for j in range(len(seq2)):
            if seq1[i] == seq2[j]:
                lengths[i + 1][j + 1] = lengths[i][j] + 1
            else:
                lengths[i + 1][j + 1] = max(lengths[i + 1][j], lengths[i][j + 1])

    return 1 - 2 * lengths[-1][-1] / (len(seq1) + len(seq2))


def lev_distance(x, y):
    return textdistance.levenshtein.normalized_distance(x, y)


def euc_distance(x, y):
    return textdistance.cosine.normalized_distance(x, y)


def jaccard_distance(x, y):
    return textdistance.jaccard.normalized_distance(x.split(), y.split())


def ratcliff_distance(x, y):
    return textdistance.ratcliff_obershelp.normalized_distance(x, y)


def min_distance(c_set, t_set):
    D = []
    for c_inst in c_set:
        min_candidate_distance = 1e10
        for t_inst in t_set:
            min_candidate_distance = min(min_candidate_distance, jaccard_distance(c_inst, t_inst))
        D.append(min_candidate_distance)
    return D


def adaptive_random_sampling(logs, labels=None, shot=8):
    if shot >= len(logs):
        return list(zip(logs, labels))
    if labels is None:
        labels = logs.copy()
    sample_set = []
    T = []
    while shot > 0:
        if len(sample_set) == 0:
            i = max(range(0, len(logs)), key=lambda x: (
                len(logs[x].split()), len(logs[x])))
            T.append(logs[i])
            sample_set.append((logs[i], labels[i]))
            del logs[i], labels[i]
            shot -= 1
            continue
        n_candidate = min(8, len(logs))
        candidate_set = random.sample(list(zip(logs, labels, range(len(logs)))), n_candidate)
        candidate_set = sorted(
            candidate_set, key=lambda x: len(x[0]), reverse=True)
        candidate_distance = min_distance([x[0] for x in candidate_set], T)
        best_candidate = max(range(len(candidate_distance)),
                             key=candidate_distance.__getitem__)
        T.append(candidate_set[best_candidate][0])
        sample_set.append((candidate_set[best_candidate][0], candidate_set[best_candidate][1]))
        del logs[candidate_set[best_candidate][2]], labels[candidate_set[best_candidate][2]]
        shot -= 1
    return sample_set


class Vocab:
    def __init__(self, log_func=print, stopwords=["<*>"]):
        self.log_func = log_func
        stopwords = [
            "a",
            "an",
            "and",
            "i",
            "ie",
            "so",
            "to",
            "the",

        ] + list(calendar.day_name) + list(calendar.day_abbr) \
          + list(calendar.month_name) + list(calendar.month_abbr)
        self.token_counter = Counter()
        self.stopwords = frozenset(set(stopwords))
        #print(self.__filter_stopwords(['LDAP', 'Built', 'with']))

    def build(self, sequences):
        self.log_func(f"Build vocab with examples: {len(sequences)}")
        for i, sequence in enumerate(sequences):
            if i % 1000 == 0:  # Log progress every 1000 sequences
                self.log_func(f"Building vocabulary: processing sequence {i}/{len(sequences)}...")
            try:
                sequence = self.__filter_stopwords(sequence)
                #print(sequence)
                self.update(sequence)
            except Exception as e:
                self.log_func(f"ERROR: Failed to process sequence {i}: {str(e)}")
                raise e
        self.log_func("Vocabulary building completed successfully")

    def update(self, sequence):
        sequence = self.__filter_stopwords(sequence)
        self.token_counter.update(sequence)

    def topk_tokens(self, sequence, topk=3):
        try:
            sequence = self.__filter_stopwords(sequence)
            token_count = [(token, self.token_counter[token]) for token in set(sequence)]
            topk_tuples = heapq.nlargest(topk, token_count, key=lambda x: x[1])
            topk_keys = tuple([t[0] for t in topk_tuples])
            return topk_keys
        except Exception as e:
            self.log_func(f"ERROR: topk_tokens failed for sequence: {str(e)}")
            raise e

    def __len__(self):
        return len(self.token_counter)

    def __filter_stopwords(self, sequence):
        return [
            token
            for token in sequence
            if (len(token) > 2) and (token not in self.stopwords)
        ]


def clean(s, log_func=print):
    """
    Clean and normalize log entry for processing.
    
    Args:
        s: Raw log string
        log_func: Function to use for logging
        
    Returns:
        tuple: (cleaned_text, log_format)
    """
    try:
        if not isinstance(s, str) or len(s.strip()) == 0:
            log_func(f"Warning: Empty or invalid log entry: {repr(s)}")
            return "", ""
        
        # Extract log format (special characters)
        log_format = re.sub(r'[0-9A-Za-z, ]+', '', s)
        unique_chars = list(set(log_format))
        sorted_string = ''.join(sorted(unique_chars))
        
        # Clean the text content
        cleaned = re.sub(':|\(|\)|=|,|"|\{|\}|@|$|\[|\]|\||;|\.?!', ' ', s)
        cleaned = " ".join([word for word in cleaned.strip().split() if not bool(re.search(r'\d', word))])
        
        if len(cleaned.split()) == 0:
            log_func(f"Warning: Log entry resulted in empty text after cleaning: {repr(s)}")
            return "", sorted_string
            
        return cleaned, sorted_string
        
    except Exception as e:
        log_func(f"ERROR: Clean function failed for string '{str(s)[:100]}...': {str(e)}")
        raise e


def hierarchical_clustering(contents, log_func=print):
    """
    Perform hierarchical clustering on log entries.
    
    Args:
        contents: Dictionary of {index: (cleaned_text, log_format)}
        log_func: Function to use for logging
        
    Returns:
        Dictionary containing hierarchical cluster information
    """
    if not contents:
        raise ValueError("No contents provided for clustering")
    
    log_func(f"Building vocabulary from {len(contents)} log entries...")
    vocab = Vocab(log_func)
    
    # Prepare sequences for vocabulary building
    sequences = []
    for idx, (text, _) in contents.items():
        if text and len(text.split()) > 0:
            sequences.append(text.split())
    
    if not sequences:
        raise ValueError("No valid sequences found for vocabulary building")
    
    vocab.build(sequences)
    log_func(f"Vocabulary built with {len(vocab)} unique tokens")

    # hierarchical clustering
    log_func("Starting hierarchical clustering...")
    hierarchical_clusters = {}
    
    log_func("Processing each log entry...")
    processed_count = 0
    for i, (k, v) in enumerate(contents.items()):
        if i % 1000 == 0:  # Log progress every 1000 entries
            log_func(f"Processing entry {i}/{len(contents)}...")
        
        try:
            text, log_format = v
            if not text or len(text.split()) == 0:
                continue
                
            frequent_token = tuple(sorted(vocab.topk_tokens(text.split(), 3)))
            if not frequent_token:
                continue
                
            if frequent_token not in hierarchical_clusters:
                hierarchical_clusters[frequent_token] = {"size": 1, "cluster": {log_format: [k]}}
            else:
                hierarchical_clusters[frequent_token]["size"] = hierarchical_clusters[frequent_token]["size"] + 1
                if log_format not in hierarchical_clusters[frequent_token]["cluster"]:
                    hierarchical_clusters[frequent_token]["cluster"][log_format] = [k]
                else:
                    hierarchical_clusters[frequent_token]["cluster"][log_format].append(k)
            
            processed_count += 1
            
        except Exception as e:
            log_func(f"Warning: Failed to process entry {k}: {str(e)}")
            continue
    
    log_func(f"Successfully processed {processed_count} entries")
    log_func(f"Number of coarse-grained clusters: {len(hierarchical_clusters.keys())}")
    
    total_fine_clusters = 0
    for k, v in hierarchical_clusters.items():
        total_fine_clusters += len(hierarchical_clusters[k]["cluster"])
    
    log_func(f"Number of fine-grained clusters: {total_fine_clusters}")
    
    if len(hierarchical_clusters) == 0:
        raise ValueError("No clusters created. Check if your log entries are too similar or empty after cleaning.")
    
    # Check if all logs are identical (only one cluster)
    if len(hierarchical_clusters) == 1:
        log_func("Warning: All log entries appear to be identical. This may cause issues with sampling.")
        # Check if we have enough variety in the single cluster
        first_cluster = list(hierarchical_clusters.values())[0]
        if len(first_cluster["cluster"]) == 1:
            log_func("Warning: Only one fine-grained cluster found. Consider using a smaller shot size or checking data variety.")
    
    log_func("Hierarchical clustering completed successfully")
    return hierarchical_clusters


def hierarchical_distribute(hierarchical_clusters, shot, logs=[], labels=[], log_func=print):
    """
    Distribute samples across hierarchical clusters.
    
    Args:
        hierarchical_clusters: Clusters from hierarchical clustering
        shot: Number of samples to generate
        logs: Original log entries
        labels: Original labels
        log_func: Function to use for logging
        
    Returns:
        List of (log, label) samples
    """
    if not hierarchical_clusters:
        raise ValueError("No hierarchical clusters provided")
    
    if shot <= 0:
        raise ValueError(f"Invalid shot number: {shot}")
    
    log_func(f"Starting hierarchical distribution for {shot} shots...")
    candidate_samples = []
    
    coarse_clusters = list(hierarchical_clusters.keys())
    if not coarse_clusters:
        raise ValueError("No coarse clusters available")
    
    coarse_clusters = shuffle(coarse_clusters)
    corase_size = len(coarse_clusters)
    log_func(f"Processing {corase_size} coarse clusters...")
    
    # Calculate quotas for each coarse cluster
    coarse_quotas = [0] * corase_size
    remaining_shots = shot
    
    while remaining_shots > 0:
        round_quota = 0
        for coarse_id, coarse_key in enumerate(coarse_clusters):
            if coarse_quotas[coarse_id] >= hierarchical_clusters[coarse_key]["size"]:
                continue
                
            # Calculate quota for this cluster
            base_quota = remaining_shots // corase_size
            extra_quota = 1 if coarse_id < remaining_shots % corase_size else 0
            available_quota = hierarchical_clusters[coarse_key]["size"] - coarse_quotas[coarse_id]
            
            coarse_quota = min(base_quota + extra_quota, available_quota)
            if coarse_quota == 0:
                coarse_quota = 1
                
            coarse_quotas[coarse_id] += coarse_quota
            round_quota += coarse_quota
            
            if round_quota >= remaining_shots:
                break
                
        remaining_shots -= round_quota
    
    log_func(f"Coarse quotas calculated: {coarse_quotas}")
    
    # Generate samples from each cluster
    for coarse_id, coarse_key in enumerate(coarse_clusters):
        coarse_quota = coarse_quotas[coarse_id]
        if coarse_quota == 0:
            continue
            
        log_func(f"Processing coarse cluster {coarse_id + 1}/{corase_size} with quota {coarse_quota}")
        
        fine_clusters = list(hierarchical_clusters[coarse_key]["cluster"].keys())
        fine_clusters = sorted(fine_clusters, key=lambda x: len(hierarchical_clusters[coarse_key]["cluster"][x]), reverse=True)
        fine_size = len(fine_clusters)
        
        if fine_size == 0:
            log_func(f"Warning: No fine clusters in coarse cluster {coarse_id + 1}")
            continue
            
        # Calculate quotas for fine clusters
        fine_quotas = [0] * fine_size
        remaining_fine_quota = coarse_quota
        
        while remaining_fine_quota > 0:
            round_quota = 0
            for fine_id, fine_key in enumerate(fine_clusters):
                if fine_quotas[fine_id] >= len(hierarchical_clusters[coarse_key]["cluster"][fine_key]):
                    continue
                    
                # Calculate quota for this fine cluster
                base_quota = remaining_fine_quota // fine_size
                extra_quota = 1 if fine_id < remaining_fine_quota % fine_size else 0
                available_quota = len(hierarchical_clusters[coarse_key]["cluster"][fine_key]) - fine_quotas[fine_id]
                
                fine_quota = min(base_quota + extra_quota, available_quota)
                if fine_quota == 0:
                    fine_quota = 1
                    
                fine_quotas[fine_id] += fine_quota
                round_quota += fine_quota
                
                if round_quota >= remaining_fine_quota:
                    break
                    
            remaining_fine_quota -= round_quota

        log_func(f"Fine quotas for cluster {coarse_id + 1}: {fine_quotas}")

        # Generate samples from fine clusters
        for fine_id, fine_key in enumerate(fine_clusters):
            fine_quota = fine_quotas[fine_id]
            if fine_quota == 0:
                break

            cluster_ids = hierarchical_clusters[coarse_key]["cluster"][fine_key]
            if not cluster_ids:
                continue
                
            cluster_logs = [logs[i] for i in cluster_ids if i < len(logs)]
            cluster_labels = [labels[i] for i in cluster_ids if i < len(labels)]
            
            if len(cluster_logs) == 0:
                log_func(f"Warning: No valid logs in fine cluster {fine_id + 1}")
                continue

            if fine_quota > len(cluster_logs):
                log_func(f"Warning: Requested {fine_quota} samples but only {len(cluster_logs)} available")
                fine_quota = len(cluster_logs)

            # Randomly sample from the cluster
            samples = random.sample(list(zip(cluster_logs, cluster_labels)), fine_quota)
            candidate_samples.extend(samples)
            log_func(f"Added {fine_quota} samples from fine cluster {fine_id + 1}")

    log_func(f"Hierarchical distribution completed. Total samples: {len(candidate_samples)}")
    
    if len(candidate_samples) == 0:
        raise ValueError("No samples generated. Check cluster configuration and quotas.")
    
    return candidate_samples


def sampling(logs, labels=None, shots=[8], log_func=print):
    """
    Hierarchical sampling function with detailed logging.
    
    Args:
        logs: List of log entries
        labels: List of corresponding labels
        shots: List of shot numbers to sample
        log_func: Function to use for logging (default: print)
    """
    log_func(f"Starting hierarchical clustering for {len(logs)} log entries...")
    
    # Process all logs (no deduplication - each log entry is unique)
    contents = {}
    for i, x in enumerate(logs):
        try:
            x_clean, fx = clean(x, log_func)
            if len(x_clean.split()) > 0:
                contents[i] = (x_clean, fx)
        except Exception as e:
            log_func(f"Warning: Failed to clean log entry {i}: {str(e)}")
            # Skip this entry but continue
            continue
    
    log_func(f"Successfully processed {len(contents)} log entries...")
    
    if len(contents) == 0:
        raise ValueError("No valid log entries found after cleaning. Check your data format.")
    
    log_func(f"Starting hierarchical clustering for {len(contents)} log entries...")
    begin_time = time.time()
    
    try:
        hierarchical_clusters = hierarchical_clustering(contents, log_func)
        end_time = time.time()
        clustering_time = end_time - begin_time
        log_func(f"Hierarchical clustering completed in {clustering_time:.4f} seconds")
    except Exception as e:
        log_func(f"ERROR: Hierarchical clustering failed: {str(e)}")
        raise e
    
    sample_candidates = {}
    total_shots = len(shots)
    
    for idx, shot in enumerate(shots):
        log_func(f"Starting {shot}-shot sampling ({idx + 1}/{total_shots})...")
        
        # Validate shot size vs available data
        total_available_samples = sum(len(cluster["cluster"]) for cluster in hierarchical_clusters.values())
        if shot > total_available_samples:
            log_func(f"Warning: Requested {shot} samples but only {total_available_samples} fine-grained clusters available.")
            
            # Suggest appropriate shot sizes
            suggested_shots = []
            for suggested_shot in [1, 2, 3, 4, 5, 8, 16, 32]:
                if suggested_shot <= total_available_samples:
                    suggested_shots.append(suggested_shot)
            
            if suggested_shots:
                suggested_str = ", ".join(map(str, suggested_shots))
                log_func(f"Suggested shot sizes for this dataset: {suggested_str}")
            
            log_func(f"Reducing shot size from {shot} to {total_available_samples}")
            shot = total_available_samples
        
        begin_time = time.time()
        try:
            samples = hierarchical_distribute(deepcopy(hierarchical_clusters), shot, logs, labels, log_func)
            sample_candidates[shot] = samples
            end_time = time.time()
            log_func(f"{shot}-shot sampling completed in {end_time - begin_time:.4f} seconds")
            log_func(f"Generated {len(samples)} samples for {shot}-shot")
        except Exception as e:
            log_func(f"ERROR: {shot}-shot sampling failed: {str(e)}")
            raise e

    log_func("All sampling completed successfully!")
    return sample_candidates



def hierarchical_distribute2(hierarchical_clusters, shot, logs=[], labels=[]):
    candidate_samples = []
    coarse_clusters = hierarchical_clusters.keys()
    # coarse_clusters = shuffle(list(coarse_clusters))
    coarse_clusters = sorted(coarse_clusters, key=lambda x: hierarchical_clusters[x]["size"], reverse=True)
    corase_size = len(coarse_clusters)
    coarse_quotas = [0] * corase_size
    while shot > 0:
        round_quota = 0
        for coarse_id, coarse_key in enumerate(coarse_clusters):
            if coarse_quotas[coarse_id] == hierarchical_clusters[coarse_key]["size"]:
                continue
            coarse_quota = min(int(shot // corase_size) + (coarse_id < shot % corase_size), hierarchical_clusters[coarse_key]["size"] - coarse_quotas[coarse_id])
            if coarse_quota == 0:
                coarse_quota = 1
            coarse_quotas[coarse_id] += coarse_quota
            round_quota += coarse_quota
            if round_quota == shot:
                break
        shot -= round_quota
    for coarse_id, coarse_key in enumerate(coarse_clusters):
        coarse_quota = coarse_quotas[coarse_id]
        logs_ids = []
        for _, log_ids in hierarchical_clusters[coarse_key]["cluster"].items():
            logs_ids.extend(log_ids)
        logs = [logs[i] for i in logs_ids]
        labels = [labels[i] for i in logs_ids]
        samples = adaptive_random_sampling(logs, labels, coarse_quota)
        candidate_samples.extend(samples)

    return candidate_samples
