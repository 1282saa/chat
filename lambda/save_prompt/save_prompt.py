import json
def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"success": True, "message": "프롬프트 처리 완료"}, ensure_ascii=False)
    }
