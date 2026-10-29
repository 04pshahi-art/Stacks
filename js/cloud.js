(() => {
  const config = window.STACKS_CONFIG || {};
  const configured = /^https:\/\/[\w-]+\.supabase\.co$/.test(config.supabaseUrl || '') &&
    typeof config.supabaseAnonKey === 'string' && config.supabaseAnonKey.length > 20;
  window.stacksCloudReady = configured
    ? import('https://esm.sh/@supabase/supabase-js@2').then(({ createClient }) => ({
        client: createClient(config.supabaseUrl, config.supabaseAnonKey), configured: true
      }))
    : Promise.resolve({ client: null, configured: false });
})();
