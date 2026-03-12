from run import parse_screen_json


def test_parse_screen_json():
    raw = '''Here's my proposal:
```json
{
  "name": "test",
  "hypothesis": "testing",
  "filters": [{"feature": "return_3m", "op": ">", "value": 0.05}],
  "top_n": 20
}
```
'''
    screen = parse_screen_json(raw)
    assert screen["name"] == "test"
    assert len(screen["filters"]) == 1
    assert screen["top_n"] == 20


def test_parse_screen_json_no_codeblock():
    raw = '{"name": "test", "hypothesis": "x", "filters": [], "top_n": 10}'
    screen = parse_screen_json(raw)
    assert screen["name"] == "test"
