"""
Search bars for purchase order creator
"""
from flask import render_template, request
from flask_login import login_required
from app import db
from app.logger import get_logger

logger = get_logger("asset_management.routes.inventory.searchbars")


def register_search_bars_routes(inventory_bp):
    """Register search bars routes to the inventory blueprint"""
    
    # Part search for purchase order creator
    @inventory_bp.route('/purchase-orders/search-bars/parts')
    @login_required
    def search_bars_parts():
        """HTMX endpoint to return part search results"""
        try:
            from app.data.core.supply.part_definition import PartDefinition
            
            search = request.args.get('search', '').strip()
            limit = request.args.get('limit', type=int, default=10)
            selected_part_id = request.args.get('selected_part_id', type=int)
            
            query = PartDefinition.query.filter(PartDefinition.status == 'Active')
            
            if search:
                query = query.filter(
                    db.or_(
                        PartDefinition.part_number.ilike(f'%{search}%'),
                        PartDefinition.part_name.ilike(f'%{search}%'),
                        PartDefinition.description.ilike(f'%{search}%')
                    )
                )
            
            parts = query.order_by(PartDefinition.part_name).limit(limit).all()
            total_count = query.count()
            
            return render_template(
                'inventory/ordering/search_bars/parts_results.html',
                parts=parts,
                total_count=total_count,
                showing=len(parts),
                search=search,
                selected_part_id=selected_part_id
            )
        except Exception as e:
            logger.error(f"Error in parts search: {e}")
            return render_template(
                'inventory/ordering/search_bars/parts_results.html',
                parts=[],
                total_count=0,
                showing=0,
                search=search or '',
                error=str(e)
            ), 500

    # Part search for *unlinked* purchase order creator (page-specific)
    @inventory_bp.route('/create-unlinked-purchase-order/search-bars/parts')
    @login_required
    def search_bars_parts_unlinked_po():
        """HTMX endpoint to return full searchbar with dropdown for unlinked PO page only."""
        try:
            from app.data.core.supply.part_definition import PartDefinition

            # HTMX sends the input field's 'name' attribute as the parameter
            # Accept both 'search' and 'unlinked_part_search' for flexibility
            search = (request.args.get("unlinked_part_search") or request.args.get("search") or "").strip()
            limit = request.args.get("limit", type=int, default=10)
            selected_part_id = request.args.get("selected_part_id", type=int)

            logger.info(f"Unlinked PO parts search: search='{search}', limit={limit}, all_args={dict(request.args)}")

            parts = []
            total_count = 0

            # Only search if we have a search term
            if search:
                query = PartDefinition.query.filter(PartDefinition.status == "Active").filter(
                    db.or_(
                        PartDefinition.part_number.ilike(f"%{search}%"),
                        PartDefinition.part_name.ilike(f"%{search}%"),
                        PartDefinition.description.ilike(f"%{search}%"),
                    )
                )

                parts = query.order_by(PartDefinition.part_name).limit(limit).all()
                total_count = query.count()

                logger.info(f"Found {len(parts)} parts (showing {len(parts)} of {total_count} total)")

            # Return the full searchbar partial (input + dropdown)
            return render_template(
                "inventory/purchase_orders/search_bars/unlinked_part_searchbar.html",
                parts=parts,
                total_count=total_count,
                showing=len(parts),
                search=search,
                selected_part_id=selected_part_id,
            )
        except Exception as e:
            logger.error(f"Error in unlinked PO parts search: {e}", exc_info=True)
            return (
                render_template(
                    "inventory/purchase_orders/search_bars/unlinked_part_searchbar.html",
                    parts=[],
                    total_count=0,
                    showing=0,
                    search=(request.args.get("unlinked_part_search") or request.args.get("search") or "").strip(),
                    error=str(e),
                ),
                500,
            )












