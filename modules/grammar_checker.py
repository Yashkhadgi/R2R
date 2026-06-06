import language_tool_python
import spacy
from typing import List, Dict, Optional, Tuple
import re
import math

def check_grammar(paper_data: dict) -> dict:
    """
    Checks grammar quality of all sections in the paper.
    Returns structured result with score, error counts, and suggestions.
    """
    try:
        # Initialize LanguageTool and spaCy
        tool = language_tool_python.LanguageTool('en-US')
        nlp = spacy.load('en_core_web_sm')

        sections = paper_data.get('sections', {})
        total_words = paper_data.get('total_words', 0)

        # Master counters
        total_errors = 0
        errors_by_category = {
            'SPELLING': 0,
            'GRAMMAR': 0,
            'PUNCTUATION': 0,
            'STYLE': 0,
            'OTHER': 0
        }
        errors_by_section = {}

        # Process each section
        for section_name, section_data in sections.items():
            text = section_data.get('text', '')
            word_count = section_data.get('word_count', 0)

            # Skip very short sections
            if word_count < 50:
                continue

            # Run LanguageTool on section text
            matches = tool.check(text)

            section_error_count = 0
            section_top_errors = []

            for match in matches:
                # Map category
                cat_raw = ''
                if hasattr(match, 'category'):
                    cat_raw = str(match.category).upper()
                elif hasattr(match, 'ruleId'):
                    cat_raw = str(match.ruleId).upper()

                if 'TYPO' in cat_raw or 'SPELL' in cat_raw:
                    category = 'SPELLING'
                elif 'GRAMMAR' in cat_raw:
                    category = 'GRAMMAR'
                elif 'PUNCT' in cat_raw:
                    category = 'PUNCTUATION'
                elif 'STYLE' in cat_raw:
                    category = 'STYLE'
                else:
                    category = 'OTHER'

                errors_by_category[category] += 1
                section_error_count += 1
                total_errors += 1

                # Collect top 5 errors per section
                if len(section_top_errors) < 5:
                    # Get context safely
                    if hasattr(match, 'context'):
                        context_str = str(match.context)
                    else:
                        offset = getattr(match, 'offset', 0)
                        start = max(0, offset - 30)
                        end = min(len(text), offset + 30)
                        context_str = text[start:end]

                    section_top_errors.append({
                        'message': str(getattr(match, 'message', '')),
                        'context': context_str,
                        'category': category,
                        'offset': int(getattr(match, 'offset', 0))
                    })

            # Calculate error density for this section
            section_density = round(
                (section_error_count / word_count) * 100, 2
            ) if word_count > 0 else 0.0

            errors_by_section[section_name] = {
                'error_count': section_error_count,
                'error_density': section_density,
                'top_errors': section_top_errors
            }

        # Close LanguageTool
        tool.close()

        # Overall error density
        error_density = round(
            (total_errors / total_words) * 100, 2
        ) if total_words > 0 else 0.0

        # Score calculation
        grammar_score = round(max(0.0, 100.0 - (error_density * 5)), 2)

        # Status
        if grammar_score >= 80:
            status = 'good'
        elif grammar_score >= 60:
            status = 'acceptable'
        else:
            status = 'needs_improvement'

        # Worst sections — top 3 by error_density
        sorted_sections = sorted(
            errors_by_section.items(),
            key=lambda x: x[1]['error_density'],
            reverse=True
        )
        worst_sections = [s[0] for s in sorted_sections[:3]]

        # Suggestions based on dominant category
        dominant_cat = max(errors_by_category, key=errors_by_category.get)
        suggestions = []

        if dominant_cat == 'SPELLING':
            suggestions.append(
                'Run a dedicated spell-check pass — spelling errors are the dominant issue.'
            )
        elif dominant_cat == 'GRAMMAR':
            suggestions.append(
                'Review sentence structure — grammatical errors are the dominant issue.'
            )
        elif dominant_cat == 'PUNCTUATION':
            suggestions.append(
                'Review punctuation usage throughout — especially commas and apostrophes.'
            )
        elif dominant_cat == 'STYLE':
            suggestions.append(
                'Consider simplifying sentence style — style warnings are frequent.'
            )
        else:
            suggestions.append(
                'Review flagged errors manually for miscellaneous issues.'
            )

        suggestions.append(
            'Review the worst-scoring sections manually: ' + ', '.join(worst_sections)
        )
        suggestions.append(
            'Consider using Grammarly or similar tools for a final pass before submission.'
        )

        return {
            'grammar_score': grammar_score,
            'total_errors': total_errors,
            'error_density': error_density,
            'errors_by_category': errors_by_category,
            'errors_by_section': errors_by_section,
            'worst_sections': worst_sections,
            'suggestions': suggestions,
            'status': status
        }

    except Exception as e:
        return {
            'grammar_score': 0.0,
            'total_errors': 0,
            'error_density': 0.0,
            'errors_by_category': {
                'SPELLING': 0,
                'GRAMMAR': 0,
                'PUNCTUATION': 0,
                'STYLE': 0,
                'OTHER': 0
            },
            'errors_by_section': {},
            'worst_sections': [],
            'suggestions': [],
            'status': 'error',
            'error': str(e)
        }


def get_grammar_summary(result: dict) -> str:
    """
    Returns a 2-3 sentence plain English summary of the grammar result.
    """
    if result.get('status') == 'error':
        return 'Grammar check could not be completed due to an error.'

    score = result.get('grammar_score', 0)
    total = result.get('total_errors', 0)
    density = result.get('error_density', 0)
    status = result.get('status', '')
    worst = result.get('worst_sections', [])

    summary = (
        f"The paper received a grammar score of {score}/100 ({status}), "
        f"with {total} total errors detected at a density of {density} errors per 100 words. "
    )

    if worst:
        summary += f"The sections requiring most attention are: {', '.join(worst)}."
    else:
        summary += "No specific sections were flagged as problematic."

    return summary