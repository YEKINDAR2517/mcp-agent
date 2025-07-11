from flask import Flask, Response, request, jsonify
import json
import time
import datetime
import subprocess
import psutil
import platform
import requests
from typing import List, Dict, Any
import re
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_sse(data: str, event=None) -> str:
    """格式化 SSE 消息"""
    msg = f'data: {data}\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg + '\n'

def verify_token(request):
    """验证请求的 token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split(' ')[1]
    return token == 'token1'  # 与配置文件中的 token 匹配

@app.route('/sse')
def sse():
    """SSE 端点"""
    if not verify_token(request):
        return 'Unauthorized', 401

    # 获取channel参数
    channel = request.args.get('channel', 'default')
    
    # 获取功能参数
    function = request.args.get('function', '')
    params = json.loads(request.args.get('params', '{}'))

    logger.info(f"收到SSE请求: function={function}, params={params}")

    def generate():
        """生成 SSE 事件流"""
        try:
            # 根据请求的功能执行相应的操作
            if function == 'search':
                logger.info(f"调用 handle_search, params={params}")
                result = handle_search(params)
            elif function == 'execute':
                logger.info(f"调用 handle_execute, params={params}")
                result = handle_execute(params)
            elif function == 'analyze_code':
                logger.info(f"调用 handle_analyze_code, params={params}")
                result = handle_analyze_code(params)
            elif function == 'system_info':
                logger.info(f"调用 handle_system_info")
                result = handle_system_info()
            elif function == 'weather':
                logger.info(f"调用 handle_weather, params={params}")
                result = handle_weather(params)
            elif function == 'translate':
                logger.info(f"调用 handle_translate, params={params}")
                result = handle_translate(params)
            elif function == 'summarize':
                logger.info(f"调用 handle_summarize, params={params}")
                result = handle_summarize(params)
            elif function == 'code_review':
                logger.info(f"调用 handle_code_review, params={params}")
                result = handle_code_review(params)
            elif function == 'get_current_date':
                logger.info(f"调用 get_current_date")
                result = get_current_date()
            elif function == 'get_date_after_n_days':
                logger.info(f"调用 get_date_after_n_days, params={params}")
                result = get_date_after_n_days(params['n'])
            else:
                logger.info(f"未知功能，进入长连接心跳: {function}")
                try:
                    while True:
                        yield format_sse(json.dumps({"pong": True}))
                        time.sleep(5)
                except GeneratorExit:
                    logger.info("SSE连接关闭，心跳循环退出")
                return

            # 发送功能执行结果
            logger.info(f"功能 {function} 返回: {result}")
            yield format_sse(json.dumps(result, ensure_ascii=False), event=function)

        except Exception as e:
            error_result = {
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }
            logger.error(f"功能 {function} 执行异常: {e}")
            yield format_sse(json.dumps(error_result, ensure_ascii=False), event='error')

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    )

def handle_search(params: dict) -> dict:
    logger.info(f"handle_search 被调用, params={params}")
    """处理搜索请求"""
    query = params.get('query', '')
    search_type = params.get('type', 'web')  # 支持不同类型的搜索
    
    if search_type == 'web':
        # 模拟网络搜索结果
        return {
            'query': query,
            'type': 'web',
            'timestamp': datetime.datetime.now().isoformat(),
            'results': [
                {
                    'title': f'搜索结果 1 - {query}',
                    'url': f'https://example.com/1?q={query}',
                    'snippet': '这是第一个搜索结果的摘要...'
                },
                {
                    'title': f'搜索结果 2 - {query}',
                    'url': f'https://example.com/2?q={query}',
                    'snippet': '这是第二个搜索结果的摘要...'
                }
            ]
        }
    elif search_type == 'local':
        # 本地文件搜索
        try:
            result = subprocess.run(
                f"find . -type f -name '*{query}*'",
                shell=True,
                capture_output=True,
                text=True
            )
            files = result.stdout.strip().split('\n')
            return {
                'query': query,
                'type': 'local',
                'timestamp': datetime.datetime.now().isoformat(),
                'results': [{'path': f} for f in files if f]
            }
        except Exception as e:
            return {'error': str(e)}

def handle_execute(params: dict) -> dict:
    logger.info(f"handle_execute 被调用, params={params}")
    """处理命令执行请求"""
    command = params.get('command', '')
    timeout = params.get('timeout', 30)
    
    # 检查命令安全性
    dangerous_commands = ["rm -rf", "mkfs", "dd", "format", ">", ">>", "&", "|"]
    if any(cmd in command.lower() for cmd in dangerous_commands):
        raise ValueError("不允许执行危险命令")
    
    try:
        process = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        return {
            'command': command,
            'exit_code': process.returncode,
            'stdout': process.stdout,
            'stderr': process.stderr,
            'timestamp': datetime.datetime.now().isoformat()
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"命令执行超时: {timeout}秒")

def handle_analyze_code(params: dict) -> dict:
    logger.info(f"handle_analyze_code 被调用, params={params}")
    """处理代码分析请求"""
    code = params.get('code', '')
    
    # 简单的代码分析逻辑
    lines = code.splitlines()
    functions = [line for line in lines if line.strip().startswith('def ')]
    imports = [line for line in lines if line.strip().startswith('import ') or line.strip().startswith('from ')]
    
    return {
        'language': 'python',  # 简单判断语言
        'lines': len(lines),
        'functions': functions,
        'imports': imports,
        'timestamp': datetime.datetime.now().isoformat()
    }

def handle_system_info() -> dict:
    logger.info(f"handle_system_info 被调用")
    """处理系统信息请求"""
    return {
        'cpu': {
            'count': psutil.cpu_count(),
            'percent': psutil.cpu_percent(interval=1)
        },
        'memory': {
            'total': psutil.virtual_memory().total // (1024 * 1024 * 1024),  # GB
            'available': psutil.virtual_memory().available // (1024 * 1024 * 1024),  # GB
            'percent': psutil.virtual_memory().percent
        },
        'os': {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version()
        },
        'timestamp': datetime.datetime.now().isoformat()
    }

def handle_weather(params: dict) -> dict:
    logger.info(f"handle_weather 被调用, params={params}")
    """获取天气信息
    
    参数:
        city: 城市名称
        date: 目标日期（YYYY-MM-DD），不能为空
    """
    city = params.get('city', '北京')
    date = params.get('date')
    if not date:
        raise ValueError('date参数不能为空')
    # 查询明天的日期
    tomorrow = get_date_after_n_days(1)
    forecast = [
        {'date': tomorrow, 'high': 26, 'low': 15, 'condition': '晴'},
        {'date': get_date_after_n_days(2), 'high': 24, 'low': 14, 'condition': '多云'},
        {'date': get_date_after_n_days(3), 'high': 23, 'low': 13, 'condition': '小雨'}
    ]
    # 查找目标日期的天气
    weather_info = next((f for f in forecast if f['date'] == date), None)
    if not weather_info:
        weather_info = {'date': date, 'high': 22, 'low': 12, 'condition': '未知'}
    return {
        'city': city,
        'date': date,
        'tomorrow': tomorrow,
        'timestamp': datetime.datetime.now().isoformat(),
        'weather': weather_info,
        'forecast': forecast
    }

def handle_translate(params: dict) -> dict:
    logger.info(f"handle_translate 被调用, params={params}")
    """文本翻译
    
    参数:
        text: 要翻译的文本
        from_lang: 源语言（默认自动检测）
        to_lang: 目标语言（默认中文）
    """
    text = params.get('text', '')
    from_lang = params.get('from_lang', 'auto')
    to_lang = params.get('to_lang', 'zh')
    
    # 模拟翻译结果
    translations = {
        'hello': '你好',
        'world': '世界',
        'python': 'Python编程语言',
        'artificial intelligence': '人工智能'
    }
    
    return {
        'text': text,
        'from_lang': from_lang,
        'to_lang': to_lang,
        'timestamp': datetime.datetime.now().isoformat(),
        'translation': translations.get(text.lower(), f'[翻译: {text}]'),
        'alternatives': [f'备选翻译 {i+1}' for i in range(2)]
    }

def handle_summarize(params: dict) -> dict:
    logger.info(f"handle_summarize 被调用, params={params}")
    """文本摘要
    
    参数:
        text: 要总结的文本
        max_length: 最大摘要长度（单词数）
    """
    text = params.get('text', '')
    max_length = params.get('max_length', 100)
    
    # 简单的摘要生成逻辑
    sentences = text.split('。')
    summary = '。'.join(sentences[:2]) + '。' if len(sentences) > 2 else text
    
    return {
        'text': text,
        'max_length': max_length,
        'timestamp': datetime.datetime.now().isoformat(),
        'summary': summary,
        'original_length': len(text),
        'summary_length': len(summary)
    }

def handle_code_review(params: dict) -> dict:
    logger.info(f"handle_code_review 被调用, params={params}")
    """代码审查
    
    参数:
        code: 要审查的代码
        language: 编程语言
    """
    code = params.get('code', '')
    language = params.get('language', 'python')
    
    # 简单的代码审查逻辑
    issues = []
    
    if language == 'python':
        # 检查一些常见问题
        if 'print' in code:
            issues.append({
                'type': 'style',
                'message': '建议使用日志而不是 print 语句'
            })
        if 'except:' in code:
            issues.append({
                'type': 'warning',
                'message': '不要使用空的 except 语句'
            })
        if len(code.splitlines()) > 50:
            issues.append({
                'type': 'info',
                'message': '考虑将代码拆分为更小的函数'
            })
    
    return {
        'language': language,
        'timestamp': datetime.datetime.now().isoformat(),
        'issues': issues,
        'suggestions': [
            '添加更多的注释',
            '考虑添加类型提示',
            '添加单元测试'
        ],
        'metrics': {
            'lines': len(code.splitlines()),
            'complexity': len(re.findall(r'if|for|while|def|class', code))
        }
    }

def get_current_date() -> str:
    """获取当前日期（YYYY-MM-DD）"""
    return datetime.datetime.now().strftime('%Y-%m-%d')

def get_date_after_n_days(n: int) -> str:
    """获取n天后的日期（YYYY-MM-DD），n可为正负整数"""
    target_date = datetime.datetime.now() + datetime.timedelta(days=n)
    return target_date.strftime('%Y-%m-%d')

@app.route('/')
def home():
    """首页，显示使用说明"""
    return '''
    <h1>SSE 测试服务器</h1>
    <p>访问 /sse 端点获取事件流，需要：</p>
    <ul>
        <li>Authorization: Bearer token1</li>
        <li>可选参数：channel（默认为 default）</li>
        <li>功能参数：
            <ul>
                <li>function: 功能名称</li>
                <li>params: JSON 格式的参数</li>
            </ul>
        </li>
    </ul>
    <h2>可用功能：</h2>
    <pre>
    1. 搜索功能
       /sse?function=search&params={"query":"测试","type":"web"}
       /sse?function=search&params={"query":"test","type":"local"}
    
    2. 执行命令
       /sse?function=execute&params={"command":"ls","timeout":30}
    
    3. 代码分析
       /sse?function=analyze_code&params={"code":"def hello():\\n    print('hello')"}
    
    4. 系统信息
       /sse?function=system_info
       
    5. 天气查询
       /sse?function=weather&params={"city":"北京"}
       
    6. 文本翻译
       /sse?function=translate&params={"text":"hello","from_lang":"en","to_lang":"zh"}
       
    7. 文本摘要
       /sse?function=summarize&params={"text":"这是一段很长的文本...","max_length":100}
       
    8. 代码审查
       /sse?function=code_review&params={"code":"def test():\\n    print('test')","language":"python"}
    </pre>
    '''

@app.route('/list_tools')
def mcp_functions():
    """返回所有支持的 MCP 功能及参数说明"""
    functions = [
        {
            "name": "search",
            "description": "搜索信息（支持 web 和 local）",
            "params": [
                {"name": "query", "type": "str", "desc": "搜索关键词"},
                {"name": "type", "type": "str", "desc": "搜索类型（web/local）"}
            ]
        },
        {
            "name": "execute",
            "description": "执行命令",
            "params": [
                {"name": "command", "type": "str", "desc": "要执行的命令"},
                {"name": "timeout", "type": "int", "desc": "超时时间（秒）"}
            ]
        },
        {
            "name": "analyze_code",
            "description": "代码分析",
            "params": [
                {"name": "code", "type": "str", "desc": "要分析的代码"}
            ]
        },
        {
            "name": "system_info",
            "description": "获取系统信息",
            "params": []
        },
        {
            "name": "weather",
            "description": "天气查询",
            "params": [
                {"name": "city", "type": "str", "desc": "城市名称"},
                {"name": "date", "type": "str", "desc": "目标日期（YYYY-MM-DD，可由get_date_after_n_days生成）"}
            ]
        },
        {
            "name": "translate",
            "description": "文本翻译",
            "params": [
                {"name": "text", "type": "str", "desc": "要翻译的文本"},
                {"name": "from_lang", "type": "str", "desc": "源语言"},
                {"name": "to_lang", "type": "str", "desc": "目标语言"}
            ]
        },
        {
            "name": "summarize",
            "description": "文本摘要",
            "params": [
                {"name": "text", "type": "str", "desc": "要总结的文本"},
                {"name": "max_length", "type": "int", "desc": "最大摘要长度"}
            ]
        },
        {
            "name": "code_review",
            "description": "代码审查",
            "params": [
                {"name": "code", "type": "str", "desc": "要审查的代码"},
                {"name": "language", "type": "str", "desc": "编程语言"}
            ]
        },
        {
            "name": "get_current_date",
            "description": "获取当天日期（YYYY-MM-DD），可用于需要当前日期的参数补全。",
            "params": []
        },
        {
            "name": "get_date_after_n_days",
            "description": "计算n天后的日期（YYYY-MM-DD），可用于weather等方法的date参数。",
            "params": [
                {"name": "n", "type": "int", "desc": "天数，可为正负整数"}
            ]
        }
    ]
    return jsonify({"functions": functions})

if __name__ == '__main__':
    app.run(host='localhost', port=3002, debug=False, threaded=True) 