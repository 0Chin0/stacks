import logging

from flask import (
    current_app,
    jsonify,
    request,
)

from . import api_bp
from stacks.security.auth import (
    require_auth_with_permissions,
)

logger = logging.getLogger("api")


def get_queue_ops():
    """Get the queue operations instance for multi-process mode."""
    from stacks.coordinator.queue_ops import QueueOperations
    return QueueOperations()


@api_bp.route('/api/history/clear', methods=['POST'])
@require_auth_with_permissions(allow_downloader=False)
def api_history_clear():
    """Clear entire history"""
    if current_app.stacks_multiprocess:
        # Multi-process mode: use queue_ops
        ops = get_queue_ops()
        count = ops.clear_history()
    else:
        # Debug mode: use old queue
        q = current_app.stacks_queue
        count = q.clear_history()

    return jsonify({
        'success': True,
        'message': f'Cleared {count} item(s) from history'
    })


@api_bp.route('/api/history/retry', methods=['POST'])
@require_auth_with_permissions(allow_downloader=False)
def api_history_retry():
    """Retry a failed download"""
    data = request.json
    md5 = data.get('md5')

    if not md5:
        return jsonify({'success': False, 'error': 'MD5 required'}), 400

    if current_app.stacks_multiprocess:
        # Multi-process mode: use queue_ops
        ops = get_queue_ops()
        success, message = ops.retry_failed(md5)
    else:
        # Debug mode: use old queue
        q = current_app.stacks_queue
        success, message = q.retry_failed(md5)

    return jsonify({
        'success': success,
        'message': message
    })


@api_bp.route('/api/history/retry_all', methods=['POST'])
@require_auth_with_permissions(allow_downloader=False)
def api_history_retry_all():
    """
    Retry ALL failed downloads at once.

    Previously only single-item retry was available (POST /api/history/retry).
    This endpoint handles bulk retry so users don't need to click each item individually.
    """
    if current_app.stacks_multiprocess:
        ops = get_queue_ops()
        success, message, count = ops.retry_all_failed()
    else:
        q = current_app.stacks_queue
        success, message, count = q.retry_all_failed()

    return jsonify({
        'success': success,
        'message': message,
        'count': count
    })
