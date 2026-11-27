"""Compare evidence selection, English thesis generation, and ISIC reranking offline."""
import argparse
from collections import Counter
import json
from pathlib import Path
from http.client import HTTPConnection
from time import monotonic

from semiotic_language import WORDS
from semiotic_specialists import Language, SectorRanker


def ask(port, alias, rules, prompt, fields, max_tokens=144):
    schema = {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
    payload = {'model': alias, 'temperature': 0, 'max_tokens': max_tokens,
               'chat_template_kwargs': {'enable_thinking': False},
               'response_format': {'type': 'json_object', 'schema': schema},
               'messages': [{'role': 'system', 'content': rules}, {'role': 'user', 'content': prompt}]}
    connection = HTTPConnection('127.0.0.1', port, timeout=75)
    try:
        connection.request('POST', '/v1/chat/completions', json.dumps(payload).encode(), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f'inference_http_{response.status}')
        choice = json.loads(response.read(65536))['choices'][0]
        if choice['finish_reason'] != 'stop':
            raise ValueError('incomplete_response')
        return json.loads(choice['message']['content'])
    finally:
        connection.close()


def enum(choices):
    return {'type': 'string', 'enum': list(choices)}


def timed(case, operation):
    started = monotonic()
    try:
        result = operation()
    except (ValueError, RuntimeError, LookupError, OSError) as exc:
        result = {'status': 'rejected', 'error': str(exc)[:200]}
    return {'case': case['id'], **result, 'seconds': round(monotonic() - started, 3)}


def check_thesis(language, case, text, quote_id):
    text = text.strip()
    if not text or quote_id == 'none':
        return {'status': 'abstained'}
    evidence = next((row for row in case['evidence'] if row['id'] == quote_id), None)
    if evidence is None:
        raise ValueError('unknown_evidence_id')
    word_count = len(WORDS.findall(text))
    if not 4 <= word_count <= 19:
        raise ValueError(f'word_count_{word_count}')
    if language.detect(text) != 'en':
        raise ValueError('english_check_failed')
    return {'status': 'passes_automatic_checks', 'thesis': text, 'word_count': word_count, 'evidence': evidence}


def run_theses(cases, assets, alias, port):
    language = Language(assets)

    def thesis(case):
        if alias == 'extract-and-translate':
            span = case['evidence'][0]
            text = span['quote']
            if case['language'] != 'en':
                text, = language.translate([text], case['language'])
            return check_thesis(language, case, text, span['id'])
        evidence = {item['id']: item['quote'] for item in case['evidence']}
        rules = ('Use the supplied source excerpts as evidence. Write the document’s main finding or stated purpose '
                     'in English in 4–19 words. Preserve uncertainty. Pick the evidence ID that directly supports '
                     'the resulting statement. If evidence is insufficient, return empty English and evidence_id none.')
        if case.get('focused_evidence'):
            rules += (' Use only facts from this single evidence span. Preserve the exact metric, date and degree of certainty '
                      'if you mention them. For dataset documentation, summarize the data described and omit publication scheduling details.')
        result = ask(port, alias, rules,
                     json.dumps({'document_type': case['document_type'], 'excerpts': evidence}, ensure_ascii=False),
                     {'english': {'type': 'string'}, 'evidence_id': enum([*evidence, 'none'])})
        return check_thesis(language, case, result['english'], result['evidence_id'])

    return [timed(case, lambda: thesis(case)) for case in cases]


def positive_notes(row):
    return ' '.join([row['name'], row['includes']])[:1800]


def retrieval(data, assets):
    ranker = SectorRanker(assets)
    codes = ranker.codes
    notes = data['sections']
    queries = [f"query: The actor {row['actor']} ({row['role']}) carries out {row['activity']}."
               for row in data['isic']]
    q = ranker.embed(queries)
    broad = q @ ranker.section_vectors.T
    enriched = q @ ranker.embed(['passage: ' + positive_notes(notes[code]) for code in codes]).T
    for case, a, b in zip(data['isic'], broad.tolist(), enriched.tolist(), strict=True):
        def top(values):
            return [codes[i] for i in sorted(range(len(codes)), key=lambda i: (-values[i], codes[i]))[:5]]
        case['titles_only'] = top(a)
        case['shortlist'] = top(b)
    return data


class NLIReranker:
    def __init__(self, path):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True).eval()
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.entailment = next(int(k) for k, value in self.model.config.id2label.items() if value.lower() == 'entailment')

    def probabilities(self, sentence, hypotheses):
        import torch

        samples = self.tokenizer([sentence] * len(hypotheses), hypotheses, padding=True, truncation=True,
                                 max_length=384, return_tensors='pt')
        with torch.inference_mode():
            return self.model(**samples).logits.softmax(dim=-1)[:, self.entailment].tolist()

    def classify(self, case, notes):
        evidence = f"Actor: {case['actor']}. Role: {case['role']}. Activity: {case['activity']}. {case['quote']}"
        choices = case['shortlist']
        scores = self.probabilities(evidence, [
            f"The target actor carries out an economic activity in {notes[code]['name']}. Examples: {notes[code]['includes'][:280]}"
            for code in choices])
        exclusions = [code for code in choices if notes[code]['excludes']]
        if exclusions:
            exclusions_scores = self.probabilities(evidence, [
                f"The actor performs one of these excluded activities: {notes[code]['excludes'][:280]}"
                for code in exclusions])
            for code, score in zip(exclusions, exclusions_scores, strict=True):
                scores[choices.index(code)] *= 1 - 0.25 * score
        ranked = sorted(zip(choices, scores, strict=True), key=lambda item: -item[1])
        top, confidence = ranked[0]
        # Fixed for this exploratory benchmark. Scores require separate calibration.
        supported = confidence >= 0.55 and confidence - ranked[1][1] >= 0.1
        return {'status': 'candidate' if supported else 'abstained', 'code': top if supported else None,
                'ranked': [[code, round(p, 4)] for code, p in ranked]}


def run_isic(data, alias, port, model_path):
    notes = data['sections']
    nli = NLIReranker(model_path) if alias == 'mdeberta' else None

    def classify(case):
        if nli:
            return nli.classify(case, notes)
        choices = case['shortlist']
        context = {code: {'name': notes[code]['name'], 'includes': notes[code]['includes'][:380],
                          'excludes': notes[code]['excludes'][:380]} for code in choices}
        result = ask(port, alias,
                     'Classify only the supplied actor’s documented economic activity using the ISIC Rev. 5 choices. '
                     'Return none for missing activity, incidental sector mentions, plans, or insufficient evidence.',
                     json.dumps({'actor': case['actor'], 'role': case['role'], 'activity': case['activity'],
                                 'quote': case['quote'], 'choices': context}, ensure_ascii=False),
                     {'code': enum([*choices, 'none'])})
        code = result['code']
        if code not in [*choices, 'none']:
            raise ValueError('out_of_shortlist')
        return {'status': 'candidate' if code != 'none' else 'abstained', 'code': None if code == 'none' else code}

    return [timed(case, lambda: classify(case)) for case in data['isic']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=('retrieve', 'thesis', 'isic'))
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model')
    parser.add_argument('--port', type=int, default=18082)
    parser.add_argument('--nli-path', type=Path)
    args = parser.parse_args()
    import torch

    torch.set_num_threads(4)
    data = json.loads(args.input.read_bytes())
    if args.task == 'retrieve':
        result = retrieval(data, args.assets)
    else:
        rows = (run_theses(data['thesis'], args.assets, args.model, args.port) if args.task == 'thesis' else
                run_isic(data, args.model, args.port, args.nli_path))
        result = {'model': args.model, 'rows': rows}
        print(args.task, args.model, dict(Counter(row['status'] for row in rows)), flush=True)
    with args.output.open('w', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
