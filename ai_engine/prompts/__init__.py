from .formatter import (
    FORMATTER_SYSTEM,
    build_formatter_prompt,
    build_formatter_prompt_with_context,
    fallback_formal_text,
)

from .summarizer import (
    SUMMARIZER_SYSTEM,
    build_summary_prompt,
    fallback_summary,
    fallback_priority,
)

from .reply_suggest import (
    REPLY_SYSTEM,
    build_reply_prompt,
    fallback_reply,
)

from .feedback import (
    FEEDBACK_SYSTEM,
    build_feedback_prompt,
    fallback_feedback_insight,
)

from .executive import (
    EXECUTIVE_SYSTEM,
    build_executive_prompt,
    fallback_executive_recommendations,
)



__all__ = [
    'FORMATTER_SYSTEM',
    'build_formatter_prompt',
    'build_formatter_prompt_with_context',
    'fallback_formal_text',

    'SUMMARIZER_SYSTEM',
    'build_summary_prompt',
    'fallback_summary',
    'fallback_priority',

    'REPLY_SYSTEM',
    'build_reply_prompt',
    'fallback_reply',

    'FEEDBACK_SYSTEM',
    'build_feedback_prompt',
    'fallback_feedback_insight',

    'EXECUTIVE_SYSTEM',
    'build_executive_prompt',
    'fallback_executive_recommendations',
]