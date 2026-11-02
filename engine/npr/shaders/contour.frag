#version 330 core
// Passe contour : Sobel 3x3 sur les normales (vecteurs) et sur log(profondeur).
// Les G-buffers sont échantillonnés en GL_NEAREST : aucune interpolation.
// Référence numpy : reference.contour.
in vec2 v_uv;
out vec4 FragColor;

uniform sampler2D couleur;        // sortie de la passe d'ombrage
uniform sampler2D gNormal;
uniform sampler2D gDepth;

uniform vec2 texelSize;           // (1/W, 1/H)
uniform int epaisseur;            // pas en texels (entier >= 1)
uniform float normalThreshold;
uniform float depthThreshold;
uniform float farLog;             // log(profondeur_fond), substitué au fond
uniform vec3 outlineColor;
uniform vec3 backgroundColor;

float logProf(vec2 uv) {
    float d = texture(gDepth, uv).r;
    return d > 0.0 ? log(d) : farLog;
}

void main() {
    float dc = texture(gDepth, v_uv).r;
    if (dc <= 0.0) {                      // fond : pas de trait
        FragColor = vec4(backgroundColor, 1.0);
        return;
    }

    vec2 o = texelSize * float(epaisseur);
    vec3 nN[9];
    float lD[9];
    int k = 0;
    for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
            vec2 p = v_uv + vec2(float(i), float(j)) * o;
            nN[k] = texture(gNormal, p).xyz;
            lD[k] = logProf(p);
            k++;
        }
    }

    // Indices : 0 1 2 = ligne basse (y-), 3 4 5 = centre, 6 7 8 = ligne haute (y+).
    vec3 gx = (nN[2] + 2.0 * nN[5] + nN[8]) - (nN[0] + 2.0 * nN[3] + nN[6]);
    vec3 gy = (nN[6] + 2.0 * nN[7] + nN[8]) - (nN[0] + 2.0 * nN[1] + nN[2]);
    float edN = length(gx) + length(gy);

    float gxd = (lD[2] + 2.0 * lD[5] + lD[8]) - (lD[0] + 2.0 * lD[3] + lD[6]);
    float gyd = (lD[6] + 2.0 * lD[7] + lD[8]) - (lD[0] + 2.0 * lD[1] + lD[2]);
    float edD = abs(gxd) + abs(gyd);

    vec3 col = texture(couleur, v_uv).rgb;
    if (edN > normalThreshold || edD > depthThreshold) {
        col = outlineColor;
    }
    FragColor = vec4(col, 1.0);
}
