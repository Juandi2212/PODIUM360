// config.js
// Archivo de configuración compartido para Supabase

const SUPABASE_URL = 'https://ssvnixnqczpvpiomgrje.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_F3JgCtnvCVkAUJegIQ5IQA_uMK2oMwk';

let supabaseClient = null;

function getSupabase() {
    if (supabaseClient) return supabaseClient;
    
    if (typeof window.supabase !== 'undefined' && typeof window.supabase.createClient === 'function') {
        supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    } else if (typeof supabase !== 'undefined' && typeof supabase.createClient === 'function') {
        supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    } else {
        console.error("No se pudo inicializar Supabase. El script de Supabase JS no cargó.");
    }
    return supabaseClient;
}

// Global exposure
window.getSupabase = getSupabase;
