"""Read-only evidence collection from the final Neo4j lab graph."""
from pathlib import Path
import json
from bench_kg import connect_graph
from src.graph_retrieval import snapshot

QUERIES = {
    'labels': 'MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC',
    'relationships': 'MATCH ()-[r]->() RETURN type(r) AS relationship, count(*) AS n ORDER BY n DESC',
    'constraints': 'SHOW CONSTRAINTS YIELD name,type,labelsOrTypes,properties RETURN name,type,labelsOrTypes,properties',
    'node_property_keys': 'MATCH (n) UNWIND keys(n) AS key RETURN labels(n)[0] AS label,collect(DISTINCT key) AS keys ORDER BY label',
    'huy_highest_clause': "MATCH (a:Article {id:'Điều 250 BLHS'})-[:HAS_CLAUSE]->(cl:Clause {number:4}) RETURN a.id AS article,cl.text AS text",
    'huy_cases': "MATCH (p:Person {name:'Cái Quang Huy'})-[r:INVOLVED_IN]->(k:Case) "
                 'RETURN p.name AS person, k.name AS case_name, k.doc_id AS doc_id, r.charge AS charge',
    'nato_law': "MATCH (p:Person {name:'Dương Minh Tuấn'})-[:INVOLVED_IN]->(:Case)-[:CHARGED_WITH]->"
                '(:Crime)<-[:DEFINES]-(a:Article)-[:HAS_CLAUSE]->(cl:Clause) '
                'RETURN DISTINCT a.id AS article,cl.number AS clause,cl.text AS text ORDER BY article,clause',
    'mdma_cases': "MATCH (k:Case)-[r:INVOLVES]->(s:Substance {name:'MDMA'}) "
                  'RETURN k.name AS case_name,k.doc_id AS doc_id,r.amount AS amount,r.source_doc_ids AS sources',
    'orphan_cases': 'MATCH (k:Case) WHERE NOT (k)-[:CHARGED_WITH]->() RETURN k.name AS name,k.doc_id AS doc_id',
    'missing_charge': "MATCH (p:Person)-[r:INVOLVED_IN]->(k:Case) WHERE r.charge = '' "
                      'RETURN p.name AS person,r.role AS role,k.name AS case_name,k.doc_id AS doc_id',
    'embedding_counts': 'MATCH (n) RETURN count(n) AS nodes,count(n.embedding) AS embedded_nodes,'
                        'collect(DISTINCT n.embedding_model) AS models,collect(DISTINCT size(n.embedding)) AS dimensions',
    'missing_provenance': 'MATCH ()-[r]->() WHERE size(coalesce(r.source_doc_ids,[]))=0 RETURN count(r) AS count',
}


def main():
    graph = connect_graph()
    try:
        evidence = {name: {'cypher': q, 'rows': graph.run(q)} for name, q in QUERIES.items()}
        evidence['stats'] = graph.stats()
        path = Path('report/graph_evidence.json')
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        Path('.cache').mkdir(exist_ok=True)
        Path('.cache/final_graph_snapshot.json').write_text(json.dumps(snapshot(graph), ensure_ascii=False), encoding='utf-8')
        print('Saved graph evidence:', evidence['stats'])
    finally:
        graph.close()


if __name__ == '__main__':
    main()
