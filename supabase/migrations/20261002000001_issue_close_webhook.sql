-- Close the "new PDF detected" GitHub Issue when an extraction is approved.
-- Dispatches a separate repository_dispatch event so the existing 'enrich-courses'
-- event (trigger_enricher_on_approval) is left untouched.
create or replace function trigger_issue_close_on_approval()
returns trigger
language plpgsql
security definer
as $$
declare
  github_pat text;
begin
  -- Only trigger when status transitions to 'approved'
  if new.status = 'approved' and (old.status is distinct from 'approved') then
    begin
      select decrypted_secret into github_pat
      from vault.decrypted_secrets
      where name = 'github_pat'
      limit 1;
    exception when others then
      github_pat := null;
    end;

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
          'event_type', 'extraction-approved',
          'client_payload', jsonb_build_object(
            'extraction_id', new.id,
            'pdf_url', new.pdf_url
          )
        )
      );
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists on_extractions_approved_issue_close on extractions;
create trigger on_extractions_approved_issue_close
  after update on extractions
  for each row
  execute function trigger_issue_close_on_approval();
