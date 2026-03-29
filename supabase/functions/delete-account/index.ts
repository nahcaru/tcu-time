import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type"
};
function jsonResponse(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json"
    }
  });
}
Deno.serve(async (req)=>{
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: corsHeaders
    });
  }
  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const authHeader = req.headers.get("Authorization");
    if (!supabaseUrl || !serviceRoleKey) {
      return jsonResponse({
        error: "server_error"
      }, 500);
    }
    if (!authHeader) {
      return jsonResponse({
        error: "unauthorized"
      }, 401);
    }
    const adminClient = createClient(supabaseUrl, serviceRoleKey);
    const jwt = authHeader.split(" ")[1];
    if (!jwt) {
      return jsonResponse({
        error: "unauthorized"
      }, 401);
    }
    const { data: { user }, error: userError } = await adminClient.auth.getUser(jwt);
    if (userError || !user) {
      return jsonResponse({
        error: "unauthorized"
      }, 401);
    }
    const { error: deleteError } = await adminClient.auth.admin.deleteUser(user.id);
    if (deleteError) {
      return jsonResponse({
        error: "delete_failed"
      }, 500);
    }
    return jsonResponse({
      ok: true
    }, 200);
  } catch (error) {
    console.error("delete-account failed", error);
    return jsonResponse({
      error: "server_error"
    }, 500);
  }
});
