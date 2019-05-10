uniform mat4 ModelViewProjectionMatrix;
uniform vec2 RoomPosition;
uniform vec2 RoomSize;


in vec2 pos;

void main()
{
    vec2 position = pos * RoomSize;
    position += RoomPosition;
    gl_Position = ModelViewProjectionMatrix * vec4(position, 0.0, 1.0);
}

