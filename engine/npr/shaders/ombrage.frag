#version 330 core
// Passe d'ombrage : relit le G-buffer et applique la rampe toon, la normale sphérique
// masquée, le masque d'ombre du visage, le rim light, le spéculaire durci et
// l'anisotropie des cheveux (Kajiya-Kay sur le moitié-vecteur, seuil binaire).
// Tout est calculé en espace vue. Référence numpy : reference.ombrage.
in vec2 v_uv;
out vec4 FragColor;

uniform sampler2D gAlbedo;
uniform sampler2D gNormal;
uniform sampler2D gDepth;         // r = profondeur, g,b = UV de surface
uniform sampler2D toonRampTex;    // rampe 256 x 1, GL_NEAREST
uniform sampler2D masqueSphere;   // UV de surface ; 1 = normale sphérique, 0 = normale réelle (nez)
uniform sampler2D masqueOmbre;    // UV de surface ; 1 = l'ombre de la rampe est autorisée (visage)
uniform sampler2D gTangente;      // tangente vue unitaire (zéro = pas de cheveux)
uniform sampler2D masqueCheveux;  // UV de surface ; 0 = pas de reflet de cheveux (défaut)

uniform vec2 tanFov;              // (tan(fovy/2) * aspect, tan(fovy/2))
uniform vec3 headCenter;          // centre de la tête, espace vue
uniform vec3 lightDir;            // unitaire, vers la lumière, espace vue
uniform vec3 headForward;         // unitaire, direction où regarde le visage, espace vue
uniform float sphereWeight;
uniform float faceMaskEnabled;    // 0 ou 1
uniform float faceBias;

uniform float rimThreshold;
uniform float rimSmoothness;
uniform vec3  rimColor;
uniform float specularThreshold;
uniform vec3  specularColor;

uniform float hairShift;          // décalage de la tangente le long de la normale
uniform float hairThreshold;      // seuil binaire sur sin(T', H)
uniform vec3  hairColor;

void main() {
    float d = texture(gDepth, v_uv).r;
    if (d <= 0.0) {                       // fond
        FragColor = vec4(0.0);
        return;
    }

    vec3 albedo = texture(gAlbedo, v_uv).rgb;
    vec2 ndc = v_uv * 2.0 - 1.0;
    vec3 pos = vec3(ndc.x * tanFov.x * d, ndc.y * tanFov.y * d, -d);

    vec2 uvS = texture(gDepth, v_uv).gb;   // UV de surface, pour les masques peints
    vec3 nRaw = normalize(texture(gNormal, v_uv).xyz);
    vec3 nSph = normalize(pos - headCenter);
    float w = texture(masqueSphere, uvS).r * sphereWeight;
    vec3 n = normalize(mix(nRaw, nSph, w));

    vec3 L = normalize(lightDir);
    vec3 V = normalize(-pos);

    // Demi-lambert -> coordonnée de rampe.
    float u = dot(n, L) * 0.5 + 0.5;
    if (faceMaskEnabled > 0.5) {
        vec3 Lb = normalize(lightDir + headForward * faceBias);
        float ndlb = dot(n, Lb) * 0.5 + 0.5;
        float m = texture(masqueOmbre, uvS).r;
        u = mix(1.0, ndlb, m);            // hors masque : pleine lumière
    }
    vec3 shade = texture(toonRampTex, vec2(clamp(u, 0.0, 1.0), 0.5)).rgb;
    vec3 col = albedo * shade;

    // Rim light hybride : Fresnel x éclairage direct, seuil lissé.
    float fresnel = 1.0 - max(dot(n, V), 0.0);
    float rimI = fresnel * max(dot(n, L), 0.0);
    float s = max(rimSmoothness, 1e-4);
    float rim = smoothstep(rimThreshold - s, rimThreshold + s, rimI);
    col += rim * rimColor;

    // Spéculaire durci : step sur N·H.
    vec3 H = normalize(L + V);
    float spec = step(specularThreshold, max(dot(n, H), 0.0));
    col += spec * specularColor;

    // Cheveux : sin(T', H) élevé = tangente perpendiculaire au moitié-vecteur = reflet fin.
    // Le moitié-vecteur dépend de la caméra : le reflet suit le point de vue.
    float mh = texture(masqueCheveux, uvS).r;
    vec3 T = texture(gTangente, v_uv).xyz;
    if (mh > 0.0 && length(T) > 0.5) {
        vec3 Ts = normalize(T + n * hairShift);
        float th = dot(Ts, H);
        float sinTH = sqrt(max(0.0, 1.0 - th * th));   // pas de pow() : base négative indéfinie
        col += step(hairThreshold, sinTH) * mh * hairColor;
    }

    FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
