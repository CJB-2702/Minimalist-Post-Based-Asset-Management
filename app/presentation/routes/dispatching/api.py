from flask import jsonify, request
from datetime import datetime
from app.presentation.routes.dispatching import dispatching_bp
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.major_location import MajorLocation
from app.data.dispatching.outcomes.standard_dispatch import StandardDispatch


@dispatching_bp.get('/api/assets')
def api_assets():
    asset_type_id = request.args.get('type', type=int)
    location_id = request.args.get('location', type=int)
    q = request.args.get('q', type=str)

    query = Asset.query
    if asset_type_id:
        query = query.join(AssetType).filter(AssetType.id == asset_type_id)
    if location_id:
        query = query.join(MajorLocation).filter(MajorLocation.id == location_id)
    if q:
        like = f"%{q}%"
        query = query.filter((Asset.name.ilike(like)) | (Asset.serial_number.ilike(like)))

    assets = query.limit(200).all()
    return jsonify([
        {
            'id': a.id,
            'label': a.name,
        }
        for a in assets
    ])


@dispatching_bp.get('/api/timeline')
def api_timeline():
    start = request.args.get('start')
    end = request.args.get('end')
    asset_type_id = request.args.get('assetType', type=int)
    location_id = request.args.get('location', type=int)

    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    from app.data.dispatching.request import DispatchRequest
    
    query = StandardDispatch.query.join(DispatchRequest)
    if start_dt:
        query = query.filter(StandardDispatch.scheduled_end >= start_dt)
    if end_dt:
        query = query.filter(StandardDispatch.scheduled_start <= end_dt)

    if asset_type_id:
        query = query.filter(DispatchRequest.asset_type_id == asset_type_id)
    if location_id:
        query = query.filter(DispatchRequest.major_location_id == location_id)

    dispatches = query.limit(1000).all()

    groups = {}
    items = []
    for d in dispatches:
        # Use context to access event data
        from app.buisness.dispatching.dispatch import DispatchContext
        ctx = DispatchContext.from_request_id(d.request_id)
        
        if ctx.event and ctx.event.asset_id:
            asset_id = ctx.event.asset_id
            asset = Asset.query.get(asset_id)
            if asset:
                groups[asset_id] = asset.name
        
        items.append({
            'id': d.id,
            'group': ctx.event.asset_id if ctx.event else None,
            'start': d.scheduled_start.isoformat() if d.scheduled_start else None,
            'end': d.scheduled_end.isoformat() if d.scheduled_end else None,
            'type': 'range',
            'className': 'dispatch-active' if d.status in ('Active', 'Dispatched') else 'dispatch-reserved',
            'title': ctx.request.asset_subclass_text if ctx.request else 'Dispatch',
        })

    return jsonify({
        'groups': [{'id': gid, 'content': label} for gid, label in groups.items()],
        'items': items,
    })




