--$ Continue
--$ Nah

local State = {}

function State:start(args)
    queue_display_choices({ {"Continue","a"}, {"Nah","b"} })
end

function State:update(dt)
    --
end

function State:stop()
    --
end

function State:on_dialogue_response(chosen_option)
    if chosen_option == "a" then
        switch_state(self.next_states[1])
    elseif chosen_option == "b" then 
        switch_state(self.next_states[2])
    end
end

return State