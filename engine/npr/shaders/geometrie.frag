#version 330 core
// Passe géométrie (G-buffer en MRT). Sorties :
//   0 : albédo (RGB) ;
//   1 : normale vue RAW, non encodée (fond = 0) ;
//   2 : r = profondeur linéaire d = -z vue ; g, b = UV de surface (fond = 0) ;
//   3 : tangente vue unitaire (direction des mèches ; zéro = pas de cheveux).
// Les masques du visage et des cheveux sont peints en UV : l'ombrage les lit grâce à g, b.
in vec3 v_pos_vue;
in vec3 v_normale_vue;
in vec3 v_tangente_vue;
in vec2 v_uv;

layout(location = 0) out vec4 g_albedo;
layout(location = 1) out vec4 g_normale;
layout(location = 2) out vec4 g_profondeur;
layout(location = 3) out vec4 g_tangente;

uniform sampler2D albedoTex;
uniform vec3 albedoColor;

void main() {
    g_albedo = vec4(texture(albedoTex, v_uv).rgb * albedoColor, 1.0);
    g_normale = vec4(normalize(v_normale_vue), 0.0);
    g_profondeur = vec4(-v_pos_vue.z, v_uv, 1.0);
    g_tangente = vec4(normalize(v_tangente_vue), 0.0);
}
