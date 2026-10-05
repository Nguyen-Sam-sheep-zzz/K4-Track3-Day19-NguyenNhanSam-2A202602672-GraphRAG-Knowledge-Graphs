"""Generate the comparison tables from completed experiment data, without any API calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / 'report/benchmark_kg_extended.json').read_text(encoding='utf-8'))
    assert len(data['rows']) == 40 and 'summary' in data, 'Experiment must finish before generating the report'
    summaries = data['summary']
    flat, graph = summaries['flat'], summaries['graph_bfs']
    rows = {(r['id'], r['pipeline']): r for r in data['rows']}
    def metric(key, digits=3, percent=False):
        values = [s[key] for s in (flat, graph)]
        return ' | '.join(f'{v*100:.1f}%' if percent else f'{v:.{digits}f}' for v in values)
    table = []
    for i in range(1, 21):
        ident = f'M{i:02d}'
        pair = [rows[ident, p] for p in ('flat', 'graph_bfs')]
        table.append('| ' + ident + ' | ' + pair[0]['type'] + ' | ' + ' | '.join(
            f"{r['recall']:.2f} / {r['criterion_recall']:.2f} / {r['judge']['score']} / {r['usage']['seconds']:.2f}s"
            for r in pair) + ' |')
    judge = {p: sum(r['judge_usage']['usd'] for r in data['rows'] if r['pipeline'] == p)
             for p in ('flat', 'graph_bfs')}
    kg_cost = sum(c['usd'] or 0 for c in data['baseline_index_calls'])
    traces = [r['trace'] for r in data['rows'] if r['pipeline'] == 'graph_bfs']
    text = f'''# Phần mở rộng — Node embeddings + BFS và 20 câu hỏi

**Nguyễn Nhân Sâm — 2A202602672 — 05/10/2026.** Dữ liệu gốc có 18 Điều luật, 20 bài báo, 176 chunks; graph cùng lượt chuẩn có {data['stats']['nodes']} node / {data['stats']['relationships']} cạnh. Artifact: benchmark_kg_extended.json (40 câu trả lời và trace), node_index_metadata.json, triples.json và graph_evidence.json. Bộ 6 câu/grader gốc được giữ nguyên.

## 1. Phương pháp và phạm vi

Đường OpenAI chuẩn tham chiếu là https://api.openai.com/v1; lượt thật dùng gateway tương thích https://sv.devquote.shop/v1 cho chat. Chat: {data['config']['chat_model']}; embedding: {data['config']['embedding_model']}. Cả hai pipeline dùng chung chunk 800 ký tự, top-3 vector chunks và model. Lượt mở rộng dùng lại vector chunk và KG đã trả phí ở lượt chuẩn, không đo cold indexing lần nữa. Graph có thêm node indexing được đo riêng. Các câu M01–M17 phối hợp quan hệ người/vụ/tội/luật, so sánh lượng/mức án và trạng thái; M18–M20 kiểm tra thiếu phủ luật, chất chưa xác định và sự kiện phòng ngừa. Vì vậy đây là 20 câu suy luận nhiều nguồn; không gọi mọi câu là một đường multi-hop graph thuần túy. Gold/criteria/source IDs/evidence_path nằm trong data/benchmark_kg_20.json, được thiết kế từ corpus lab, không phải benchmark độc lập của giảng viên.

Tin được LLM trích JSON người/vụ/tội/chất; luật tách bằng regex. Xuất subject–predicate–object kèm nguồn cho {data['stats']['relationships']} cạnh. Không tuyên bố toàn corpus NER bằng LLM: phần luật là parser có cấu trúc. Nếu ảnh được chấm theo yêu cầu LLM extraction cho mọi tài liệu thì cần hỏi giảng viên về cách hiểu này.

Node text ghép label/tên/id/title/summary/text/aliases, giới hạn nội dung 3500 ký tự; tạo **203 vector 3072 chiều** bằng Gemini và ghi embedding/model/text vào Neo4j. 13 batch, 16 văn bản/batch (batch cuối ít hơn); metadata chỉ xuất chiều/model/nguồn, vector đầy đủ ở Neo4j và cache local.

Query → embedding → seed: ưu tiên tất cả Person được nhắc tên/alias; nếu câu tổng hợp nhắc Substance thì ưu tiên chất; còn lại top-3 cosine node vectors. Vì có ưu tiên tên, không phải mọi seed đều được chọn thuần bằng cosine. BFS dùng queue/visited, duyệt cạnh hai chiều, tối đa **4 hop / 180 node**, loại **MENTIONS** để tránh hub chất kéo theo nhiều luật. Đây là BFS trên tập cạnh đã chọn. Serialize tối đa **100 facts**, ưu tiên văn bản khoản/summary và cạnh người/vụ/tội. LLM nhận cả facts và cùng top-3 chunks.

Trace có seed IDs, nodes, edges, đường khám phá đầu tiên theo BFS, truncated flag, facts, chunks và prompt thật. Giới hạn 4 hop áp dụng từ seed; không có nghĩa mọi fact nằm trên cùng một đường nhân quả. {sum(t['subgraph']['truncated'] for t in traces)} / 20 câu chạm giới hạn node; số node tối đa đã duyệt {max(len(t['subgraph']['nodes']) for t in traces)}, facts tối đa {max(len(t['facts']) for t in traces)}. Cắt facts vẫn có thể mất thông tin dù truncated=false (flag này chỉ báo ngân sách node).

## 2. Kết quả

Accuracy dưới đây = tỷ lệ câu được cùng LLM judge chấm **2/2** với gold; không phải accuracy do con người kiểm chứng độc lập. Keyword recall và criterion recall đều dùng substring, có thể bỏ sót diễn đạt tương đương hoặc nhận nhầm phủ định. Không đồng nhất ba thước đo.

| Chỉ số | Flat | Graph+BFS |
| --- | ---: | ---: |
| Số câu | 20 | 20 |
| Keyword recall trung bình | {metric('keyword_recall')} |
| Criterion recall trung bình | {metric('criterion_recall')} |
| Accuracy theo judge đủ ý | {metric('accuracy_judge_full', percent=True)} |
| Judge trung bình /2 | {metric('mean_judge')} |
| Latency trung bình/câu | {metric('mean_seconds', 2)} s |
| Latency p95/câu | {metric('p95_seconds', 2)} s |
| Query subtotal USD /20 câu | {metric('priced_usd_subtotal', 7)} |
| Query calls thiếu giá | {metric('unpriced_calls', 0)} |

Latency đo wall time retrieval + query embedding + chat, gồm pacing Gemini; judge đo riêng. p95 dùng nearest-rank trên 20 câu; đây là một lượt đo, không chứng minh tốc độ ổn định qua nhiều lần.

| Câu | Loại | Flat: keyword / criteria / judge / giây | BFS: keyword / criteria / judge / giây |
| --- | --- | --- | --- |
{chr(10).join(table)}

## 3. Indexing, query và judge cost

| Thành phần | Phần định giá được | Phần chưa xác định |
| --- | ---: | --- |
| Chunk indexing dùng chung từ lượt chuẩn | $0.0000000 subtotal | 176 Gemini text embeddings thiếu giá/usage; không gọi là miễn phí |
| KG extraction dùng chung từ lượt chuẩn | ${kg_cost:.7f} | 20 chat extraction; giá tham chiếu, không phải hóa đơn gateway |
| Node indexing thêm cho BFS | ${data['node_index_usage']['usd']:.7f} subtotal, {data['node_index_usage']['seconds']:.2f}s wall | {data['node_index_usage']['unpriced_calls']} batch /203 text embeddings thiếu giá/usage |
| Query Flat 20 câu | ${flat['priced_usd_subtotal']:.7f} | {flat['unpriced_calls']} Gemini query embeddings thiếu giá/usage |
| Query BFS 20 câu | ${graph['priced_usd_subtotal']:.7f} | {graph['unpriced_calls']} Gemini query embeddings thiếu giá/usage |
| Judge Flat 20 câu | ${judge['flat']:.7f} | Tách khỏi query |
| Judge BFS 20 câu | ${judge['graph_bfs']:.7f} | Tách khỏi query |

Giá chat tham chiếu gpt-6-luna: $0.10 input / $0.50 output mỗi triệu token. Google hiện niêm yết Gemini Embedding 2 ở $0.20/1M token tại https://ai.google.dev/gemini-api/docs/pricing, nhưng không niêm yết giá riêng cho gemini-embedding-001 là model đã chạy. API compatibility cũng không trả token usage, nên **chi phí thực tế embedding-001 của lượt này không xác định được**; các USD bên dưới là subtotal chat, không phải hóa đơn.

Lần node indexing đầu lỗi 429 sau 6 batch (96 văn bản); đã lưu audit/error riêng ở checkpoints/extended_batch_429_audit.json và .err, rồi thêm pacing theo số văn bản/batch. 96 embedding thành công của lần lỗi là chi phí vận hành thêm, không nằm trong node indexing 203 vector của lượt báo cáo; giá vẫn chưa biết. Tests pacing đạt. Không dùng cache để che chi phí indexing đã gọi.

## 4. Đọc kết quả và giới hạn

Phần BFS cải thiện việc đưa khoản luật vào prompt và giữ đủ quan hệ cho so sánh nhiều người. Có thể đối chiếu các câu M06 (tách tội/án), M08 (tên/alias + khung cao nhất), M10/M11 (lượng riêng và ngưỡng), M12 (hủy khởi tố, không gán cùng tội) và M14 (viên không tự đổi thành gam) trong JSON. Báo cáo chuẩn vẫn giữ Q4/Q5 chưa đủ; kết quả mở rộng không thay thế các câu chuẩn.

Không quy toàn bộ chênh lệch cho riêng BFS: pipeline này đồng thời thêm node embeddings, ưu tiên seed theo tên, loại cạnh MENTIONS và tăng ngân sách facts 60→100 so với chuẩn. Chưa có ablation Graph-Cypher/BFS trên cùng 20 câu. Gold từ corpus này và cùng model trả lời/chấm có thể thiên lệch; số liệu không chứng minh chất lượng pháp lý bên ngoài corpus.

**Lỗi còn quan sát được dù judge=2:** M17/BFS nối đúng các Điều nhưng thêm câu “Ngữ cảnh không xác định chất ma túy trong vụ của Đông có phải MDMA hay không”. Nguồn news-100260930085028036 xác nhận 0,686g MDMA tại buồng bệnh; graph_evidence cũng có lượng này. Trace M17 đã duyệt 84 node, truncated=false, nhưng 100 facts cuối không chứa 0,686g và top-3 chunk không bù được. Vì vậy model từ chối dựa trên context thiếu, rồi judge vẫn chấm 2 do gold tập trung ánh xạ tội/Điều. Đây là mất dữ kiện tại serialization cộng với tiêu chí judge chưa kiểm tra phát biểu phụ; cần dành ngân sách cho INVOLVES/amount của người/vụ được hỏi và rà claim theo nguồn. Không gọi accuracy judge là toàn bộ đáp án đúng 100%.

M15/BFS diễn đạt “1 năm đến 5 năm” tương đương “01 năm đến 05 năm” trong corpus; keyword must_include “05 năm” có thể làm recall thấp dù judge=2. Criterion recall cho phép vài diễn đạt tương đương, vẫn là kiểm tra substring và chưa thay đánh giá ngữ nghĩa.

Case dùng khóa tên còn trùng vụ Huy/Viện Pháp y; nhiều tội trong một Case có thể làm nhiễu nếu không xét charge riêng của người. Status/negation/quantities chưa có ontology sự kiện/ngưỡng riêng, nên vẫn dựa raw chunks và summary LLM. BFS loại MENTIONS cũng có thể làm mất đường hữu ích. Provenance xác định tài liệu đóng góp, không bảo đảm extraction đúng. Các câu không có Person/Crime trong graph vẫn cần fallback chunk.

## 5. Tái lập

```powershell
.\\.venv\\Scripts\\python.exe scripts/run_local.py bench_kg.py --judge
.\\.venv\\Scripts\\python.exe scripts/run_local.py bench_kg_extended.py --judge
.\\.venv\\Scripts\\python.exe scripts/run_local.py scripts/capture_graph_evidence.py
.\\.venv\\Scripts\\python.exe scripts/write_extended_report.py
```

--resume chỉ tiếp tục khi config, graph fingerprint và question hash không đổi; --check phải chạy trước benchmark chuẩn vì nó reset graph. Lượt tương lai có thể khác do gateway/extraction không hoàn toàn tái lập; giữ artifact hiện tại làm bằng chứng. Chưa commit/push hoặc nộp VLearn; bonus ontology +15 không được tuyên bố.
'''
    # Units belong in each latency cell, not just the final column.
    text = text.replace(metric('mean_seconds', 2) + ' s',
                        ' | '.join(f"{s['mean_seconds']:.2f} s" for s in (flat, graph)))
    text = text.replace(metric('p95_seconds', 2) + ' s',
                        ' | '.join(f"{s['p95_seconds']:.2f} s" for s in (flat, graph)))
    (ROOT / 'report/REPORT_KG_EXTENDED.md').write_text(text, encoding='utf-8')
    print('Saved REPORT_KG_EXTENDED.md from all 40 completed rows')


if __name__ == '__main__':
    main()
