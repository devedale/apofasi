"""
LogPPT Parser - Implementazione corretta basata sul codice ufficiale.

Questo modulo implementa il parsing dei log seguendo l'approccio originale di LogPPT:
- Tokenizzazione con delimiters personalizzati
- Parsing diretto con RoBERTa
- Generazione di template con virtual token
"""

import re
import torch
from transformers import RobertaForMaskedLM, AutoTokenizer
from logppt.postprocess import correct_single_template


class LogPPTParser:
    """
    Parser LogPPT che segue l'approccio originale.
    
    Questo parser usa RoBERTa direttamente per il parsing dei log,
    seguendo la logica implementata nel codice ufficiale di LogPPT.
    """
    
    def __init__(self, model_path="roberta-base", vtoken="<*>", use_crf=False):
        """
        Inizializza il parser LogPPT.
        
        Args:
            model_path: Path al modello RoBERTa pre-addestrato
            vtoken: Virtual token per sostituire i parametri
            use_crf: Se usare CRF per le predizioni
        """
        self.model_path = model_path
        self.vtoken = vtoken
        self.use_crf = use_crf
        
        # Delimiters per la tokenizzazione LogPPT
        self.delimiters = "([ |\(|\)|\[|\]|\{|\})])"
        
        # Carica il modello e tokenizer
        self.plm = RobertaForMaskedLM.from_pretrained(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Configura il tokenizer
        self.tokenizer.model_max_length = self.plm.config.max_position_embeddings - 2
        
        # Virtual token ID
        self.vtoken_id = self.tokenizer.convert_tokens_to_ids(vtoken)
        
        # CRF se richiesto
        if use_crf:
            from torchcrf import CRF
            self.crf = CRF(2)
    
    def tokenize_log(self, log_line, max_length=256):
        """
        Tokenizza il log usando la logica LogPPT originale.
        
        Args:
            log_line: La riga di log da tokenizzare
            max_length: Lunghezza massima della sequenza
            
        Returns:
            Dictionary con input_ids e attention_mask
        """
        # Split usando i delimiters LogPPT
        log_tokens = re.split(self.delimiters, log_line)
        log_tokens = [token for token in log_tokens if len(token) > 0]
        
        # Raffina i token come nel codice originale
        refined_tokens = []
        if log_tokens[0] != " ":
            refined_tokens.append(log_tokens[0])
        
        for i in range(1, len(log_tokens)):
            if log_tokens[i] == " ":
                continue
            if log_tokens[i - 1] == " ":
                refined_tokens.append(" " + log_tokens[i])
            else:
                refined_tokens.append(log_tokens[i])
        
        # Converti in token IDs
        token_ids = []
        for token in refined_tokens:
            ids = self.tokenizer.encode(token, add_special_tokens=False)
            token_ids.extend(ids)
        
        # Limita la lunghezza e aggiungi special tokens
        token_ids = token_ids[:max_length - 2]
        token_ids = [self.tokenizer.bos_token_id] + token_ids + [self.tokenizer.eos_token_id]
        
        return {
            'input_ids': torch.tensor([token_ids], dtype=torch.int64),
            'attention_mask': torch.tensor([[1] * len(token_ids)], dtype=torch.int64)
        }
    
    def map_template(self, inputs, labels):
        """
        Mappa i token e le label per generare il template.
        
        Args:
            inputs: Lista di token di input
            labels: Lista di label (0 per token statici, 1 per parametri)
            
        Returns:
            Template generato con virtual token
        """
        res = [" "]
        for i in range(0, len(inputs)):
            if labels[i] == 0:
                res.append(inputs[i])
            else:
                if "Ġ" in inputs[i]:
                    res.append("Ġ" + self.vtoken)
                elif self.vtoken not in res[-1]:
                    res.append(self.vtoken)
        
        r = "".join(res)
        r = r.replace("Ġ", " ")
        return r.strip()
    
    def parse_log(self, log_line, device="cpu"):
        """
        Parsa una riga di log usando l'approccio LogPPT.
        
        Args:
            log_line: La riga di log da parsare
            device: Device per l'inferenza
            
        Returns:
            Template generato con parametri sostituiti da virtual token
        """
        # Tokenizza il log
        tokenized_input = self.tokenize_log(log_line)
        tokenized_input = {k: v.to(device) for k, v in tokenized_input.items()}
        
        # Sposta il modello sul device
        self.plm.to(device)
        self.plm.eval()
        
        with torch.no_grad():
            outputs = self.plm(**tokenized_input, output_hidden_states=True)
        
        # Ottieni le predizioni
        predictions = outputs.logits.argmax(dim=-1)
        
        # Estrai i token di input (senza special tokens)
        input_tokens = self.tokenizer.convert_ids_to_tokens(
            tokenized_input['input_ids'][0]
        )[1:-1]
        
        if self.use_crf:
            # Usa CRF per le predizioni
            logits = outputs.logits[:,:,[self.vtoken_id]]
            O_logits = outputs.logits[:,:,:self.vtoken_id].max(-1)[0].unsqueeze(-1)
            logits = torch.cat([O_logits, logits], dim=-1)
            logits = logits[:, 1:-1, :]
            
            mask = tokenized_input['attention_mask'].bool()[:, 1:-1]
            labels = self.crf.viterbi_decode(logits, mask)[0]
        else:
            # Usa predizioni dirette
            logits = predictions.detach().cpu().clone().tolist()
            labels = [1 if x == self.vtoken_id else 0 for x in logits[0][1:-1]]
        
        # Genera il template
        template = self.map_template(input_tokens, labels)
        
        # Correggi il template usando la logica LogPPT
        try:
            corrected_template = correct_single_template(template)
            return corrected_template
        except:
            # Se la correzione fallisce, ritorna il template originale
            return template
    
    def parse_logs_batch(self, log_lines, device="cpu"):
        """
        Parsa multiple righe di log in batch.
        
        Args:
            log_lines: Lista di righe di log
            device: Device per l'inferenza
            
        Returns:
            Lista di template generati
        """
        results = []
        
        for i, log_line in enumerate(log_lines):
            print(f"Parsing log {i+1}/{len(log_lines)}...")
            try:
                template = self.parse_log(log_line.strip(), device)
                results.append({
                    "success": True,
                    "original_log": log_line.strip(),
                    "template": template,
                    "index": i
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "original_log": log_line.strip(),
                    "error": str(e),
                    "index": i
                })
        
        return results
    
    def save_results(self, results, output_file):
        """
        Salva i risultati del parsing.
        
        Args:
            results: Lista di risultati
            output_file: Path del file di output
        """
        import json
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Errore nel salvare i risultati: {e}")
            return False
