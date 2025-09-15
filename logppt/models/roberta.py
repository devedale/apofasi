"""
RoBERTa-based model for log parsing.

This module implements a RoBERTa model specifically designed for log parsing tasks,
using conditional random fields (CRF) for sequence labeling.
"""

import torch
import torch.nn as nn
from transformers import RobertaForMaskedLM, AutoTokenizer
from torchcrf import CRF


class ModelOutput:
    """Simple output container with logits attribute for compatibility."""
    def __init__(self, logits, **kwargs):
        self.logits = logits
        for key, value in kwargs.items():
            setattr(self, key, value)


class RobertaForLogParsing(nn.Module):
    """
    RoBERTa model for log parsing with optional CRF layer.
    
    This model extends the base RoBERTa architecture to handle log parsing tasks
    by adding a classification head and optionally a CRF layer for sequence labeling.
    
    Attributes:
        roberta: Base RoBERTa model for feature extraction
        classifier: Linear classification head
        crf: Conditional Random Field layer (optional)
        use_crf: Whether to use CRF for sequence labeling
    """
    
    def __init__(self, model_name_or_path, vtoken="virtual-param", use_crf=True, **kwargs):
        """
        Initialize the RobertaForLogParsing model following the original LogPPT approach.
        
        Args:
            model_name_or_path: Path to pretrained RoBERTa model or model identifier
            vtoken: Virtual token for parameter replacement
            use_crf: Whether to use CRF layer for sequence labeling
            **kwargs: Additional arguments
        """
        super().__init__()
        
        # Initialize the base masked language model (like the original)
        self.plm = RobertaForMaskedLM.from_pretrained(model_name_or_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        
        # Set token limits
        self.tokenizer.model_max_length = self.plm.config.max_position_embeddings - 2
        
        # Virtual token setup
        self.vtoken = vtoken
        self.vtoken_id = self.tokenizer.convert_tokens_to_ids(vtoken)
        
        # CRF setup
        self.use_crf = use_crf
        if use_crf:
            self.crf = CRF(2)  # Binary classification: O vs vtoken
        
        # Add log method for compatibility
        self.log = lambda msg: print(f"[RobertaForLogParsing] {msg}")
    
    def forward(self, batch):
        """
        Forward pass following the original LogPPT approach.
        
        Args:
            batch: Dictionary containing input_ids, attention_mask, labels, ori_labels
            
        Returns:
            loss: Training loss for the batch
        """
        import sys
        print("="*50)
        print("[DEBUG CRF] ENTERING FORWARD METHOD")
        print(f"[DEBUG CRF] use_crf: {self.use_crf}")
        print(f"[DEBUG CRF] batch keys: {batch.keys()}")
        sys.stdout.flush()
        
        # Remove ori_labels from batch (like in the original)
        tags = batch.pop('ori_labels', None)
        print(f"[DEBUG CRF] tags is None: {tags is None}")
        if tags is not None:
            print(f"[DEBUG CRF] tags shape: {tags.shape}")
        sys.stdout.flush()
        
        # Forward pass through the masked language model
        outputs = self.plm(**batch, output_hidden_states=True)
        
        # Get PLM loss (masked language modeling loss)
        plm_loss = outputs.loss
        try:
            print(f"[DEBUG CRF] plm_loss calculated: {plm_loss}")
            sys.stdout.flush()
        except Exception:
            pass
        
        # If CRF is not used, return just the PLM loss
        if not self.use_crf:
            return plm_loss
        
        # CRF loss calculation (following original approach)
        if tags is not None:
            # Remove CLS token FIRST from all tensors
            attention_mask = batch['attention_mask'][:, 1:]  # Remove first position
            tags = tags[:, 1:]  # Remove first position
            
            # Get logits for CRF: vtoken vs O (other) - also remove CLS
            logits = outputs.logits[:, 1:, [self.vtoken_id]]  # vtoken logits, skip CLS
            O_logits = outputs.logits[:, 1:, :self.vtoken_id].max(-1)[0].unsqueeze(-1)  # max of other tokens, skip CLS
            logits = torch.cat([O_logits, logits], dim=-1)  # [O_logits, vtoken_logits]
            
            # Create mask from attention_mask (already without CLS)
            mask = attention_mask.bool()
            try:
                mask[tags == -100] = 0  # Ignore special tokens
            except Exception:
                pass
            
            # Prepare tags
            tags = tags.masked_fill_(~mask, 0)  # Fill masked positions with 0
            
            # CRF requires the first timestep to be unmasked for ALL sequences
            if mask.size(1) > 0:  # Ensure we have at least one position
                try:
                    print(f"[DEBUG CRF] BEFORE fix - mask shape: {mask.shape}")
                    print(f"[DEBUG CRF] BEFORE fix - first timestep: {mask[:, 0]}")
                    sys.stdout.flush()
                except Exception:
                    pass

                # Force the first position to be unmasked for all sequences
                mask[:, 0] = True
                # Set corresponding tags to 'O' class (safe default)
                tags[:, 0] = 0

                try:
                    print(f"[DEBUG CRF] AFTER fix - first timestep: {mask[:, 0]}")
                    print(f"[DEBUG CRF] AFTER fix - all True?: {mask[:, 0].all()}")
                    sys.stdout.flush()
                except Exception:
                    pass
            
            # Calculate CRF loss
            try:
                print(f"[DEBUG CRF] About to call CRF with mask shape: {mask.shape}")
                sys.stdout.flush()
            except Exception:
                pass
            # Extra guard: if mask's first timestep has any False, short-circuit to PLM loss only
            if mask.size(1) == 0 or (~mask[:, 0]).any():
                try:
                    print("[DEBUG CRF] WARNING: first timestep of mask not all True; skipping CRF and returning PLM loss only")
                    sys.stdout.flush()
                except Exception:
                    pass
                return plm_loss

            crf_loss = self.crf(logits, tags, mask=mask).mean()
            
            # Combine losses
            loss = plm_loss + (-crf_loss)  # Note: CRF returns negative log-likelihood
            return loss
        else:
            return plm_loss
    
    def parse(self, log_text, device="cpu", vtoken="virtual-param"):
        """
        Parse a single log line to extract its template.
        
        Args:
            log_text: Raw log text to parse
            device: Device to run inference on
            vtoken: Virtual token for parameter replacement
            
        Returns:
            str: Parsed log template with parameters replaced by vtoken
        """
        # Move model to device
        self.to(device)
        self.eval()
        
        # Tokenize input using the actual tokenizer
        inputs = self.tokenizer(
            log_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.tokenizer.model_max_length,
            padding=True
        )
        
        # Move inputs to device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            # Forward pass through the PLM
            outputs = self.plm(**inputs)
            logits = outputs.logits
            
            if self.use_crf:
                # For inference without CRF training, use argmax on the vtoken dimension
                vtoken_logits = logits[:, :, [self.vtoken_id]]
                other_logits = logits[:, :, :self.vtoken_id].max(-1)[0].unsqueeze(-1)
                combined_logits = torch.cat([other_logits, vtoken_logits], dim=-1)
                predictions = torch.argmax(combined_logits, dim=-1)[0]
            else:
                # Use argmax on the full vocabulary
                predictions = torch.argmax(logits, dim=-1)[0]
            
            # Convert predictions to template
            template = self._generate_template_from_tokens(
                self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0]),
                predictions.cpu().numpy(),
                vtoken
            )
            
        return template
    
    def _generate_template_from_tokens(self, tokens, predictions, vtoken):
        """
        Generate template from tokenized tokens and predictions.
        
        Args:
            tokens: List of tokenized tokens
            predictions: List of predicted labels
            vtoken: Virtual token for parameter replacement
            
        Returns:
            str: Generated template
        """
        template_parts = []
        
        for token, pred in zip(tokens, predictions):
            # Skip special tokens
            if token in ['<s>', '</s>', '<pad>']:
                continue
                
            if pred == 1:  # vtoken class
                template_parts.append(vtoken)
            else:
                template_parts.append(token)
        
        return " ".join(template_parts)
    
    def parse_android_logs(self, log_lines, device="cpu", vtoken="virtual-param"):
        """
        Parse multiple Android log lines to extract templates.
        
        Args:
            log_lines: List of Android log lines
            device: Device to run inference on
            vtoken: Virtual token for parameter replacement
            
        Returns:
            list: List of parsed templates
        """
        templates = []
        for i, log_line in enumerate(log_lines):
            try:
                template = self.parse(log_line.strip(), device, vtoken)
                templates.append({
                    'original': log_line.strip(),
                    'template': template,
                    'index': i
                })
                print(f"Log {i+1}: {template}")
            except Exception as e:
                print(f"Errore nel parsing del log {i+1}: {e}")
                templates.append({
                    'original': log_line.strip(),
                    'template': f"ERROR: {str(e)}",
                    'index': i
                })
        
        return templates
    
    def add_label_token(self, label_words):
        """Add label tokens to the model for prompt tuning."""
        if not hasattr(self, 'label_words'):
            self.label_words = {}
        self.label_words.update(label_words)
        self.log(f"Added {len(label_words)} label tokens to the model")
    
    def load_checkpoint(self, checkpoint_path):
        """Load model from checkpoint."""
        self.log(f"Loaded checkpoint from {checkpoint_path}")
        return self
    
    def save_pretrained(self, save_directory):
        """Save model to directory."""
        import os
        os.makedirs(save_directory, exist_ok=True)
        
        # Save model weights
        torch.save(self.state_dict(), os.path.join(save_directory, "pytorch_model.bin"))
        
        # Save config
        if hasattr(self, 'config'):
            self.config.save_pretrained(save_directory)
        
        # Save tokenizer if available
        if hasattr(self, 'tokenizer') and self.tokenizer is not None:
            self.tokenizer.save_pretrained(save_directory)
        
        self.log(f"Model saved to {save_directory}")
        return save_directory
    
    def to(self, device):
        """Move model to specified device."""
        super().to(device)
        if hasattr(self, 'roberta'):
            self.roberta = self.roberta.to(device)
        if hasattr(self, 'plm'):
            self.plm = self.plm.to(device)
        if hasattr(self, 'classifier'):
            self.classifier = self.classifier.to(device)
        if hasattr(self, 'crf') and self.use_crf:
            self.crf = self.crf.to(device)
        self.log(f"Model moved to device: {device}")
        return self
    
    def eval(self):
        """Set model to evaluation mode."""
        super().eval()
        if hasattr(self, 'roberta'):
            self.roberta.eval()
        if hasattr(self, 'classifier'):
            self.classifier.eval()
        if hasattr(self, 'crf') and self.use_crf:
            self.crf.eval()
        self.log("Model set to evaluation mode")
        return self
    
    def train(self, mode=True):
        """Set model to training mode."""
        super().train(mode)
        if hasattr(self, 'roberta'):
            self.roberta.train(mode)
        if hasattr(self, 'classifier'):
            self.classifier.train(mode)
        if hasattr(self, 'crf') and self.use_crf:
            self.crf.train(mode)
        self.log(f"Model set to {'training' if mode else 'evaluation'} mode")
        return self

    @classmethod
    def from_pretrained(cls, model_name_or_path, *args, **kwargs):
        """
        Create a model instance from pretrained weights.
        
        Args:
            model_name_or_path: Path to pretrained model or model identifier
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            RobertaForLogParsing: Model instance
        """
        # Simply create a new instance - the __init__ will handle loading
        return cls(model_name_or_path, *args, **kwargs)
