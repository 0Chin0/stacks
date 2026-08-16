import logging

from flask import (
    current_app,
    jsonify,
    request,
)

from . import api_bp
from stacks.utils.md5utils import extract_md5
from stacks.security.auth import (
    require_auth,
    require_auth_with_permissions,
)

logger = logging.getLogger("api")


def get_queue_ops():
    """Get the queue operations instance for multi-process mode."""
    from stacks.coordinator.queue_ops import QueueOperations
    return QueueOperations()


@api_bp.route('/api/queue/remove', methods=['POST'])
@require_auth_with_permissions(allow_downloader=False)
def api_queue_remove():
    """Remove item from queue"""
    data = request.json
    md5 = data.get('md5')

    if not md5:
        return jsonify({'success': False, 'error': 'MD5 required'}), 400

    if current_app.stacks_multiprocess:
        # Multi-process mode: use queue_ops
        ops = get_queue_ops()
        removed = ops.remove_download(md5)
    else:
        # Debug mode: use old queue
        q = current_app.stacks_queue
        removed = q.remove_from_queue(md5)

    return jsonify({
        'success': removed,
        'message': 'Removed from queue' if removed else 'Not found in queue'
    })


@api_bp.route('/api/queue/clear', methods=['POST'])
@require_auth_with_permissions(allow_downloader=False)
def api_queue_clear():
    """Clear entire queue"""
    if current_app.stacks_multiprocess:
        # Multi-process mode: use queue_ops
        ops = get_queue_ops()
        count = ops.clear_queue()
    else:
        # Debug mode: use old queue
        q = current_app.stacks_queue
        count = q.clear_queue()

    return jsonify({
        'success': True,
        'message': f'Cleared {count} item(s) from queue'
    })


@api_bp.route('/api/queue/add', methods=['POST'])
@require_auth_with_permissions(allow_downloader=True)
def api_queue_add():
    """Add item to queue"""
    data = request.json
    md5 = data.get('md5')
    subfolder = data.get('subfolder')

    if not md5:
        return jsonify({'success': False, 'error': 'MD5 required'}), 400

    # Validate MD5
    extracted_md5 = extract_md5(md5)

    if not extracted_md5:
        return jsonify({'success': False, 'error': 'Invalid MD5 format'}), 400

    # Validate subfolder if provided
    validated_subfolder = None
    if subfolder:
        config = current_app.stacks_config
        allowed_subdirs = config.get('downloads', 'subdirectories', default=None)

        # If subfolder is provided but not in allowed list, ignore it (revert to default)
        if allowed_subdirs and isinstance(allowed_subdirs, list) and subfolder in allowed_subdirs:
            validated_subfolder = subfolder
        elif subfolder:
            logger.warning(f"Subfolder '{subfolder}' not in allowed list, reverting to default")

    # Add to queue
    if current_app.stacks_multiprocess:
        # Multi-process mode: use queue_ops
        ops = get_queue_ops()
        success, message = ops.add_download(
            extracted_md5,
            source=data.get('source'),
            subfolder=validated_subfolder
        )
    else:
        # Debug mode: use old queue
        q = current_app.stacks_queue
        success, message = q.add(
            extracted_md5,
            source=data.get('source'),
            subfolder=validated_subfolder
        )

    return jsonify({
        'success': success,
        'message': message,
        'md5': extracted_md5,
        'subfolder': validated_subfolder
    })


@api_bp.route('/api/queue/add_bulk', methods=['POST'])
@require_auth_with_permissions(allow_downloader=True)
def api_queue_add_bulk():
    """
    Add multiple items to the queue at once.

    Previously only single-item add was available (POST /api/queue/add).
    This endpoint handles bulk add so users don't need to submit each MD5 individually.

    Request body:
        {"items": [{"md5": "...", "source": "...", "subfolder": "..."}, ...]}

    Returns:
        {success, message, added, skipped, errors: [{md5, error}, ...]}
    """
    data = request.json
    items = data.get('items', [])

    if not items or not isinstance(items, list):
        return jsonify({'success': False, 'error': 'Items array required'}), 400

    added = 0
    skipped = 0
    errors = []

    config = current_app.stacks_config

    for item in items:
        raw_md5 = item.get('md5', '').strip()
        if not raw_md5:
            errors.append({'md5': raw_md5, 'error': 'Empty md5'})
            continue

        from stacks.utils.md5utils import extract_md5
        extracted_md5 = extract_md5(raw_md5)
        if not extracted_md5:
            errors.append({'md5': raw_md5, 'error': 'Invalid MD5 format'})
            continue

        subfolder = item.get('subfolder')
        validated_subfolder = None
        if subfolder:
            allowed_subdirs = config.get('downloads', 'subdirectories', default=None)
            if allowed_subdirs and isinstance(allowed_subdirs, list) and subfolder in allowed_subdirs:
                validated_subfolder = subfolder
            elif subfolder:
                logger.warning(f"Subfolder '{subfolder}' not in allowed list, reverting to default")

        if current_app.stacks_multiprocess:
            ops = get_queue_ops()
            success, message = ops.add_download(
                extracted_md5,
                source=item.get('source'),
                subfolder=validated_subfolder
            )
        else:
            q = current_app.stacks_queue
            success, message = q.add(
                extracted_md5,
                source=item.get('source'),
                subfolder=validated_subfolder
            )

        if success:
            added += 1
        else:
            skipped += 1
            errors.append({'md5': extracted_md5, 'error': message})

    return jsonify({
        'success': added > 0,
        'message': f"Added {added}, skipped {skipped} item(s)",
        'added': added,
        'skipped': skipped,
        'errors': errors
    })


@api_bp.route('/api/queue/pause', methods=['POST'])
@require_auth
def api_queue_pause():
    """Pause or resume the download worker"""
    if current_app.stacks_multiprocess:
        ops = get_queue_ops()
        currently_paused = ops.is_paused()
        ops.set_paused(not currently_paused)
        new_paused = not currently_paused
        return jsonify({
            'success': True,
            'paused': new_paused,
            'message': 'Download worker paused' if new_paused else 'Download worker resumed'
        })

    worker = current_app.stacks_worker

    # Toggle pause state
    if worker.paused:
        worker.resume()
        return jsonify({
            'success': True,
            'paused': False,
            'message': 'Download worker resumed'
        })
    else:
        worker.pause()
        return jsonify({
            'success': True,
            'paused': True,
            'message': 'Download worker paused'
        })


@api_bp.route('/api/queue/current/cancel', methods=['POST'])
@require_auth
def api_current_cancel():
    """Cancel and requeue current download"""
    if current_app.stacks_multiprocess:
        ops = get_queue_ops()
        count = ops.command_active_downloads('cancel_requeue')
        if count > 0:
            return jsonify({
                'success': True,
                'message': 'Download cancelled and added back to queue'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No download in progress'
            })

    worker = current_app.stacks_worker

    if worker.cancel_and_requeue_current():
        return jsonify({
            'success': True,
            'message': 'Download paused and added back to queue'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No download in progress'
        })


@api_bp.route('/api/queue/current/remove', methods=['POST'])
@require_auth
def api_current_remove():
    """Cancel and remove current download"""
    if current_app.stacks_multiprocess:
        ops = get_queue_ops()
        count = ops.command_active_downloads('cancel_remove')
        if count > 0:
            return jsonify({
                'success': True,
                'message': 'Stopping and removing current download'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No download in progress'
            })

    worker = current_app.stacks_worker

    if worker.cancel_and_remove_current():
        return jsonify({
            'success': True,
            'message': 'Stopping and removing current download'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No download in progress'
        })


@api_bp.route('/api/queue/current/skip', methods=['POST'])
@require_auth
def api_current_skip():
    """Skip the current download (requeue it to the end of the queue)"""
    if current_app.stacks_multiprocess:
        ops = get_queue_ops()
        count = ops.command_active_downloads('cancel_skip')
        if count > 0:
            return jsonify({
                'success': True,
                'message': 'Skipping current download (requeued to end)'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No download in progress'
            })

    worker = current_app.stacks_worker

    if worker.skip_current():
        return jsonify({
            'success': True,
            'message': 'Skipping current download (requeued to end)'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No download in progress'
        })
