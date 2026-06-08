from modules.pdf_extractor import extract_paper
from modules.vocabulary_analyzer import analyze_vocabulary

papers = [
    ('Attention', '..\\data\\sample_papers\\conference_attention.pdf'),
    ('BERT', '..\\data\\sample_papers\\conference_bert.pdf'),
    ('GPT3', '..\\data\\sample_papers\\journal_gpt3.pdf'),
    ('ResNet', '..\\data\\sample_papers\\conference_resnet.pdf'),
]

for name, path in papers:
    data = extract_paper(path)
    result = analyze_vocabulary(data)
    print(f"{name}: score={result['vocabulary_score']}, TTR={result['type_token_ratio']}, avg_len={result['avg_word_length']}, rare={result['rare_word_ratio']}, status={result['status']}")