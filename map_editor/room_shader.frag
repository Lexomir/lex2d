uniform mat4 ModelViewProjectionMatrix;
uniform vec2 RoomPosition;
uniform vec2 RoomSize;
uniform vec4 color;
uniform vec2 MousePos;
uniform int IsSelected;

in vec2 clipPos;
out vec4 fragColor;

// return the intersection point (in bounding rectangle space: (0, 1) if point is inside )
bool intersects(vec2 rectPos, vec2 rectSize, vec2 point)
{
    return (point.x >= rectPos.x) && (point.x <= rectPos.x + rectSize.x) &&
           (point.y >= rectPos.y) && (point.y <= rectPos.y + rectSize.y);
}

void main()
{
    vec4 roomClipPos = ModelViewProjectionMatrix * vec4(RoomPosition, 0, 1);
    vec4 roomClipSize = ModelViewProjectionMatrix * vec4(RoomSize, 0, 1);
    bool isHovered = intersects(RoomPosition, RoomSize, MousePos);
    vec4 color = bool(IsSelected) ? vec4(.2, .7, .5, .15) : vec4(.2, .5, .7, .25);
    vec4 hoverTint = isHovered ? vec4(.1, .1, 0, 0) :vec4(0,0,0,0);
    fragColor = color + hoverTint;
}
