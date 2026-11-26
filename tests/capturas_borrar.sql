-- Borra la cuenta de prueba de `tests/capturas.js` y todo lo suyo. Varias pasadas: así el orden de las claves no importa.
do $$
declare u bigint; t text;
begin
  select id into u from usuarias where google_sub = 'prueba-capturas';
  if u is null then return; end if;
  for pasada in 1..6 loop
    for t in select table_name from information_schema.columns
             where table_schema = 'public' and column_name = 'usuaria_id' loop
      begin execute format('delete from %I where usuaria_id = %s', t, u);
      exception when foreign_key_violation then null; end;
    end loop;
  end loop;
  delete from usuarias where id = u;
end $$;
