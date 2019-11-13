uniform vec2 DialogPosition;
uniform vec2 DialogSize;
uniform vec4 color;
uniform vec2 MousePos;

in vec2 clipPos;
out vec4 fragColor;

void main()
{
    fragColor = color;
}
