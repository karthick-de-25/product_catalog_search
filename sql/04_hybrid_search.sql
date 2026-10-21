-- Hybrid search: vector + keyword fused with Reciprocal Rank Fusion (F06).
-- Consumed by src/search/hybrid_search.py via `make search`.
--
-- Named parameters (psycopg dict):
--   %(q)s     query text (used for the query embedding AND the tsquery)
--   %(cat)s   optional category filter (NULL = all categories)
--   %(limit)s result cap
--
-- vec: top-50 semantic neighbours (ScaNN cosine on the 768-d embedding)
-- kw : top-50 keyword hits (tsvector rank)
-- RRF: score = 1/(k + rank) summed across both lists, k = 60

with vec as (
    select id,
           row_number() over (
               order by embedding <=> embedding('text-embedding-005', %(q)s)::vector
           ) as r
    from products
    where %(cat)s::text is null or category = %(cat)s
    order by embedding <=> embedding('text-embedding-005', %(q)s)::vector
    limit 50
),
kw as (
    select id,
           row_number() over (
               order by ts_rank_cd(tsv, plainto_tsquery('english', %(q)s)) desc
           ) as r
    from products
    where tsv @@ plainto_tsquery('english', %(q)s)
      and (%(cat)s::text is null or category = %(cat)s)
    limit 50
)
select p.sku, p.name, p.brand, p.category, p.size_in, p.pressure_psi, p.lead_free,
       round((coalesce(1.0 / (60.0 + vec.r), 0) + coalesce(1.0 / (60.0 + kw.r), 0))::numeric, 6) as rrf_score
from vec
full outer join kw using (id)
join products p on p.id = coalesce(vec.id, kw.id)
order by rrf_score desc
limit %(limit)s;
