uniform vec2 DialogPosition;
uniform vec2 DialogSize;
uniform mat4 ModelViewProjectionMatrix;

in vec2 pos;

void main()
{
    vec2 position = pos * DialogSize;
    position += DialogPosition;
    gl_Position = ModelViewProjectionMatrix * vec4(position, 0.0, 1.0);
}

