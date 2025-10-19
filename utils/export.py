from openpyxl import Workbook
from database.db import fetchall
def export_protections_to_xlsx(filepath, where_sql="", params=()):
    wb = Workbook(); ws = wb.active; ws.title = "Protections"
    ws.append(["ID","Dealer","City","Articles","Qty","Client","Phone4","ObjectCity","Address",
               "CreatedBy","CreatedAt","ExpiresAt","Status","BaseDays","ExtendCount","MaxExtendMgr","CloseReason","Comment"])
    rows = fetchall(f"""SELECT id,dealer,city,article,quantity,client_name,phone_last4,
        object_city,address,created_by,created_at,expires_at,status,base_days,extend_count,max_extend_manager,close_reason,comment
        FROM protections {where_sql} ORDER BY created_at DESC""", params)
    for r in rows:
        ws.append([r["id"],r["dealer"],r["city"],r["article"],r["quantity"],r["client_name"],r["phone_last4"],
                   r["object_city"],r["address"],r["created_by"],r["created_at"],r["expires_at"],r["status"],
                   r["base_days"],r["extend_count"],r["max_extend_manager"],r["close_reason"],r["comment"]])
    wb.save(filepath); return filepath
def export_stats_to_xlsx(filepath):
    wb = Workbook(); ws = wb.active; ws.title = "Stats"
    ws.append(["ManagerID","Total","Active","Closed","Closed(with reason)","Extended","Success%"])
    rows = fetchall("""SELECT created_by as mid,
        COUNT(*) total,
        SUM(CASE WHEN status IN ('active','extended','changed') THEN 1 ELSE 0 END) active_cnt,
        SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) closed_cnt,
        SUM(CASE WHEN status='closed' AND COALESCE(close_reason,'')<>'' THEN 1 ELSE 0 END) closed_with_reason,
        SUM(CASE WHEN status='extended' THEN 1 ELSE 0 END) extended_cnt
        FROM protections GROUP BY created_by ORDER BY total DESC""")
    for r in rows:
        total = r["total"] or 0
        success = (r["active_cnt"]/total*100) if total else 0
        ws.append([r["mid"],r["total"],r["active_cnt"],r["closed_cnt"],r["closed_with_reason"],r["extended_cnt"],round(success,2)])
    wb.save(filepath); return filepath
