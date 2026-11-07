-- 001_init.sql —— 内容与授权模型（M1）
--
-- 设计取舍：
-- 1. `artwork` 与 `artwork_image` 分开：一件作品在不同馆可能有多份数字副本，
--    授权与核验状态属于「副本」而不是「作品」。同一件作品的多馆副本用 work_group 归并。
-- 2. 授权门禁是视图 `v_published_artworks`，不是应用层 if：任何查询都只能从视图取
--    已发布内容，漏一处也不会把未核验的图放出去。
-- 3. verification_status / license 用 CHECK 而不是枚举类型，加值时改 CHECK 比 ALTER TYPE 省事。

begin;

create table if not exists artist (
    id          text primary key,
    name_zh     text not null,
    name_en     text,
    phase       smallint not null check (phase between 1 and 3),
    region      text not null check (region in ('cn', 'west')),
    note        text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create table if not exists artwork (
    id                bigserial primary key,
    artist_id         text not null references artist (id) on delete restrict,
    -- 同一件作品跨馆时的归并键：artist_id + 归一化标题线索
    work_group        text not null,
    title             text not null,
    title_zh          text,
    date_display      text,
    medium            text,
    dimensions        text,
    -- 归属：直标作者 / 传·摹本 / 标题命中目标作 / 匿名检索命中
    attribution_level text not null default 'unidentified_search_hit'
                      check (attribution_level in ('primary', 'copy_or_attributed',
                                                   'target_title_match', 'unidentified_search_hit')),
    target_match      text check (target_match in ('full', 'partial', 'none')),
    -- 上架开关：与「授权核验」是两个独立开关，核验通过也不代表运营已排期上架
    published         boolean not null default true,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

create index if not exists idx_artwork_artist on artwork (artist_id);
create index if not exists idx_artwork_group on artwork (work_group);

create table if not exists artwork_image (
    id                  bigserial primary key,
    artwork_id          bigint not null references artwork (id) on delete cascade,
    provider            text not null,                    -- met / cma / wikimedia / npm ...
    provider_object_id  text not null,
    holding             text,
    accession_number    text,
    license             text not null default 'UNKNOWN'
                        check (license in ('CC0', 'PDM', 'FAITHFUL_COPY', 'UNKNOWN')),
    license_evidence    text,                             -- 来源页上看到的授权依据原文
    source_url          text not null,
    image_url           text,
    image_thumb         text,
    image_profile       text,                             -- fixed-jpeg / IIIF / full TIFF ...
    credit_line         text,
    fetched_at          date,
    -- 发布门禁的判据
    verification_status text not null default 'pending'
                        check (verification_status in ('pending', 'verified', 'rejected')),
    verified_by         text,
    verified_at         timestamptz,
    -- 切片后回填
    width               int,
    height              int,
    tileset_path        text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    constraint uq_image_provider_object unique (provider, provider_object_id)
);

create index if not exists idx_image_artwork on artwork_image (artwork_id);
create index if not exists idx_image_status on artwork_image (verification_status);

-- 已发布 = 作品上架 且 至少有副本核验通过 且 授权属于可公开的三种
create or replace view v_published_artworks as
select
    a.id                as artwork_id,
    a.title,
    a.title_zh,
    a.date_display,
    a.medium,
    a.dimensions,
    a.attribution_level,
    a.target_match,
    a.work_group,
    ar.id               as artist_id,
    ar.name_zh          as artist_name_zh,
    ar.name_en          as artist_name_en,
    ar.region,
    ar.phase,
    i.id                as image_id,
    i.provider,
    i.provider_object_id,
    i.holding,
    i.accession_number,
    i.license,
    i.license_evidence,
    i.source_url,
    i.image_url,
    i.image_thumb,
    i.image_profile,
    i.credit_line,
    i.fetched_at,
    i.verification_status,
    i.width,
    i.height,
    i.tileset_path
from artwork a
join artist ar on ar.id = a.artist_id
join artwork_image i on i.artwork_id = a.id
where a.published
  and i.verification_status = 'verified'
  and i.license in ('CC0', 'PDM', 'FAITHFUL_COPY');

comment on view v_published_artworks is
    '前台唯一可用的内容视图：作品已上架 + 副本已核验 + 授权可公开。任何对外查询都走这里。';

commit;
