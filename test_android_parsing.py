#!/usr/bin/env python3
"""
Script di test per il parsing dei log Android usando il modello RoBERTa.
"""

import torch
from logppt.models.roberta import RobertaForLogParsing

def test_android_log_parsing():
    """Test del parsing dei log Android con RoBERTa."""
    
    # Log Android di esempio
    android_logs = [
        "03-17 16:13:38.811  1702  2395 D WindowManager: printFreezingDisplayLogsopening app wtoken = AppWindowToken{9f4ef63 token=Token{a64f992 ActivityRecord{de9231d u0 com.tencent.qt.qtl/.activity.info.NewsDetailXmlActivity t761}}}, allDrawn= false, startingDisplayed =  false, startingMoved =  false, isRelaunching =  false",
        "03-17 16:13:38.819  1702  8671 D PowerManagerService: acquire lock=233570404, flags=0x1, tag=\"View Lock\", name=com.android.systemui, ws=null, uid=10037, pid=2227",
        "03-17 16:13:38.820  1702  8671 D PowerManagerService: ready=true,policy=3,wakefulness=1,wksummary=0x23,uasummary=0x1,bootcompleted=true,boostinprogress=false,waitmodeenable=false,mode=false,manual=38,auto=-1,adj=0.0userId=0"
    ]
    
    print("🚀 Test del parsing dei log Android con RoBERTa")
    print("=" * 60)
    
    try:
        # Inizializza il modello (usa un modello RoBERTa base)
        print("📥 Inizializzazione del modello RoBERTa...")
        model = RobertaForLogParsing(
            model_name_or_path="roberta-base",
            use_crf=False  # Disabilita CRF per il test iniziale
        )
        print("✅ Modello inizializzato con successo!")
        
        # Test del parsing singolo
        print("\n🔍 Test del parsing singolo:")
        print("-" * 40)
        
        for i, log in enumerate(android_logs):
            print(f"\n📝 Log {i+1}:")
            print(f"Originale: {log[:100]}...")
            
            try:
                template = model.parse(log, device="cpu")
                print(f"Template:  {template}")
            except Exception as e:
                print(f"❌ Errore: {e}")
        
        # Test del parsing multiplo
        print("\n🔍 Test del parsing multiplo:")
        print("-" * 40)
        
        try:
            results = model.parse_android_logs(android_logs, device="cpu")
            print(f"\n✅ Parsing completato per {len(results)} log")
            
            # Mostra i risultati
            for result in results:
                print(f"\nLog {result['index']+1}:")
                print(f"  Originale: {result['original'][:80]}...")
                print(f"  Template:  {result['template']}")
                
        except Exception as e:
            print(f"❌ Errore nel parsing multiplo: {e}")
            
    except Exception as e:
        print(f"❌ Errore nell'inizializzazione del modello: {e}")
        print("\n💡 Suggerimenti:")
        print("   - Verifica che transformers sia installato: pip install transformers")
        print("   - Verifica che torch sia installato: pip install torch")
        print("   - Verifica la connessione internet per scaricare il modello")

if __name__ == "__main__":
    test_android_log_parsing()
