-- Enable pg_net extension for asynchronous HTTP requests from Postgres
create extension if not exists pg_net with schema extensions;

-- Function to trigger GitHub Actions enricher workflow upon extraction approval
create or replace function trigger_enricher_on_approval()
returns trigger
language plpgsql
security definer
as $$
declare
  github_pat text;
begin
  -- Only trigger when status transitions to 'approved'
  if new.status = 'approved' and (old.status is distinct from 'approved') then
    -- Retrieve decrypted GitHub PAT from Supabase Vault
    begin
      select decrypted_secret into github_pat
      from vault.decrypted_secrets
      where name = 'github_pat'
      limit 1;
    exception when others then
      github_pat := null;
    end;

    -- Dispatch GitHub Actions repository_dispatch event if PAT is configured
    if github_pat is not null and length(trim(github_pat)) > 0 then
      perform net.http_post(
        url := 'https://api.github.com/repos/nahcaru/tcu-time/dispatches',
        headers := jsonb_build_object(
          'Content-Type', 'application/json',
          'Accept', 'application/vnd.github+json',
          'Authorization', 'Bearer ' || trim(github_pat),
          'User-Agent', 'TCU-TIME-Supabase-Webhook'
        ),
        body := jsonb_build_object(
          'event_type', 'enrich-courses'
        )
      );
    end if;
  end if;

  return new;
end;
$$;

-- Create trigger on extractions table
drop trigger if exists on_extractions_approved_enricher on extractions;
create trigger on_extractions_approved_enricher
  after update on extractions
  for each row
  execute function trigger_enricher_on_approval();
