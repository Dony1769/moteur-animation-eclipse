#version 330 core
// Passe géométrie : positions et normales en espace vue, UV du maillage.
in vec3 in_position;
in vec3 in_normal;
in vec2 in_uv;

uniform mat4 modelView;
uniform mat4 projection;

out vec3 v_pos_vue;
out vec3 v_normale_vue;
out vec2 v_uv;

void main() {
    vec4 pv = modelView * vec4(in_position, 1.0);
    v_pos_vue = pv.xyz;
    // Matrice normale : suffisant tant que la transformation ne contient pas de cisaillement.
    v_normale_vue = transpose(inverse(mat3(modelView))) * in_normal;
    v_uv = in_uv;
    gl_Position = projection * pv;
}
