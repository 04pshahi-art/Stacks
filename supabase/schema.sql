-- Run this once in Supabase Dashboard > SQL Editor.
-- Book PDFs are in a private bucket. Only intentionally published metadata is public.
create extension if not exists pgcrypto;

create table if not exists public.books (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (length(title) between 1 and 180),
  author text not null default 'Unknown author' check (length(author) <= 120),
  pages integer not null default 1 check (pages > 0),
  cover_path text,
  is_published boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists books_public_title_idx on public.books (title) where is_published;
alter table public.books enable row level security;
revoke all on public.books from anon, authenticated;
-- Table-level grants are required by Supabase's Data API. RLS below limits rows.
grant select on public.books to anon, authenticated;
grant insert, update, delete on public.books to authenticated;
drop policy if exists "Owners manage their books" on public.books;
create policy "Owners manage their books" on public.books for all to authenticated
  using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
drop policy if exists "Anyone can browse published book details" on public.books;
create policy "Anyone can browse published book details" on public.books for select to anon, authenticated
  using (is_published);

create or replace function public.my_book_ids()
returns table(book_id uuid)
language sql stable security definer set search_path = ''
as $$ select b.id from public.books b where b.owner_id = (select auth.uid()) $$;
revoke all on function public.my_book_ids() from public, anon;
grant execute on function public.my_book_ids() to authenticated;

create table if not exists public.book_chapters (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references public.books(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  position integer not null check (position >= 0),
  file_name text not null,
  object_path text not null unique,
  page_count integer not null default 1 check (page_count > 0),
  created_at timestamptz not null default now(),
  unique(book_id, position)
);
alter table public.book_chapters enable row level security;
grant select, insert, update, delete on public.book_chapters to authenticated;
drop policy if exists "Owners manage their chapters" on public.book_chapters;
create policy "Owners manage their chapters" on public.book_chapters for all to authenticated
  using (owner_id = (select auth.uid()) and exists (
    select 1 from public.books b where b.id = book_id and b.owner_id = (select auth.uid())
  )) with check (owner_id = (select auth.uid()) and exists (
    select 1 from public.books b where b.id = book_id and b.owner_id = (select auth.uid())
  ));

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('book-files', 'book-files', false, 157286400, array['application/pdf'])
on conflict (id) do update set public = excluded.public,
  file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('book-covers', 'book-covers', false, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update set public = excluded.public,
  file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
drop policy if exists "Owners manage their own private book files" on storage.objects;
create policy "Owners manage their own private book files" on storage.objects for all to authenticated
  using (bucket_id = 'book-files' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'book-files' and (storage.foldername(name))[1] = (select auth.uid())::text);
drop policy if exists "Owners upload and manage their covers" on storage.objects;
create policy "Owners upload and manage their covers" on storage.objects for all to authenticated
  using (bucket_id = 'book-covers' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'book-covers' and (storage.foldername(name))[1] = (select auth.uid())::text);
drop policy if exists "Public may view book covers" on storage.objects;
drop policy if exists "Public may view published book covers" on storage.objects;
create policy "Public may view published book covers" on storage.objects for select to anon, authenticated
  using (bucket_id = 'book-covers' and exists (
    select 1 from public.books b where b.cover_path = name and b.is_published
  ));
